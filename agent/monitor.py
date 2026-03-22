"""
异步多用户监控循环（Step 7 重构）
- 从 Supabase user_settings 拉取所有开启监控的用户
- asyncio.gather 并发检查所有用户的所有监控地址
- 阻塞的 Web3 / AI 调用通过 run_in_executor 放入线程池
- 每次检查结果写入 health_history 表
- Telegram 通知用用户自己的 chat_id（Bot Token 由服务端持有）
"""

import asyncio
import os
import sys
import time
import traceback
import threading
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(".")
from read_position import get_position, get_user_collateral_breakdown, compute_weighted_thresholds
from agent import run_agent

load_dotenv("../.env")

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
POLL_INTERVAL    = int(os.getenv("MONITOR_POLL_INTERVAL", "10"))   # 主循环间隔（秒）
HISTORY_INTERVAL = 300  # 健康历史写入最低间隔（秒），控制数据库体积

# ── 每个被监控地址的上次告警记录 ─────────────────────────────────────────
# key: (user_wallet, monitored_address)
_last_alert: dict[tuple, dict] = {}

# ── 每个用户的上次检查时间 ────────────────────────────────────────────────
# key: user_wallet_address
_last_check: dict[str, datetime] = {}

# ── 每个地址的上次历史写入时间 ───────────────────────────────────────────
# key: (user_wallet, monitored_address)
_last_history_write: dict[tuple, datetime] = {}

# ── 已发过 AI Key 余额不足通知的用户 ─────────────────────────────────────
# key: user_wallet_address；充值后 AI 调用成功时自动移除
_ai_quota_alerted: set[str] = set()

# ── AI 调用串行锁（避免并发触发速率限制）─────────────────────────────────
_ai_lock = threading.Lock()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Supabase 操作（同步，在 executor 里调用）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _fetch_users() -> list[dict]:
    """拉取所有 monitor_enabled=True 的用户设置"""
    try:
        from db import supabase
        res = (
            supabase.table("user_settings")
            .select("*")
            .eq("monitor_enabled", True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"[Supabase] 拉取用户失败: {e}")
        return []


def _cleanup_old_history(retain_days: int = 7) -> None:
    """删除超过 retain_days 天的健康历史，控制数据库体积"""
    try:
        from db import supabase
        cutoff = (datetime.now() - timedelta(days=retain_days)).isoformat()
        supabase.table("health_history").delete().lt("recorded_at", cutoff).execute()
        print(f"  [cleanup] 已删除 {retain_days} 天前的历史记录")
    except Exception as e:
        print(f"  [cleanup] 清理失败: {e}")


def _write_health_history(user_wallet: str, monitored: str, pos: dict, level: str) -> None:
    """将本次检查结果写入 health_history"""
    try:
        from db import supabase
        supabase.table("health_history").insert({
            "wallet_address":    user_wallet,
            "monitored_address": monitored,
            "health_factor":     round(pos["health"], 6),
            "collateral_usd":    round(pos["collateral"], 2),
            "debt_usd":          round(pos["debt"], 2),
            "alert_level":       level,
            "recorded_at":       "now()",
        }).execute()
    except Exception as e:
        print(f"  [health_history] 写入失败: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 告警辅助
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _alert_level(health: float, alert_t: float, danger_t: float) -> str:
    if health < danger_t:
        return "DANGER"
    if health < alert_t:
        return "WARNING"
    return "SAFE"


def _level_emoji(level: str) -> str:
    return {"SAFE": "🟢 安全", "WARNING": "🟡 注意", "DANGER": "🔴 紧急"}.get(level, level)


def _should_alert(key: tuple, level: str, cooldown_w: int, cooldown_d: int) -> bool:
    """冷却控制：级别升级立即触发，否则遵守冷却时间"""
    prev = _last_alert.get(key)
    now  = datetime.now()
    if prev:
        if level == "DANGER" and prev["level"] == "WARNING":
            return True
        minutes = cooldown_d if level == "DANGER" else cooldown_w
        if now - prev["time"] < timedelta(minutes=minutes):
            remaining = int((prev["time"] + timedelta(minutes=minutes) - now).total_seconds() / 60)
            print(f"    [冷却中] 还有 {remaining} 分钟")
            return False
    return True


def _send_telegram(chat_id: str, text: str) -> None:
    if not TELEGRAM_TOKEN or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"    [Telegram] 发送失败: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI 分析（同步，给 executor 用）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _ai_analysis(pos: dict, level: str, breakdown: dict, ai_provider: str = "", ai_model: str = "", ai_api_key: str = "") -> str:
    urgency = "紧急，即将被清算" if level == "DANGER" else "警告，接近告警线"
    token_lines = ""
    weighted_liq = ""
    if breakdown and breakdown.get("collateral_tokens"):
        token_lines = "\n质押明细：\n" + "".join(
            f"  - {t['symbol']}: {t['amount']} 个 @ ${t['price_usd']:,.2f} = ${t['value_usd']:,.2f}"
            f"  清算阈值 {t['liq_threshold_pct']}\n"
            for t in breakdown["collateral_tokens"]
        )
        weighted_liq = f"加权清算阈值: {breakdown['weighted_liq_pct']}\n"

    messages = [
        {
            "role": "system",
            "content": (
                "你是 DeFi 清算保护 Agent。收到仓位告警时，必须按顺序执行：\n"
                "1. 对每种质押和借款代币调用 get_token_price 获取最新价格\n"
                "2. 同时计算两种方案：\n"
                "   方案A 还款：调用 calculate_repayment_needed\n"
                "   方案B 补仓：调用 calculate_collateral_needed（传入加权清算阈值）\n"
                "3. 综合判断是否真的需要操作\n"
                "最终建议不超过150字，必须严格按以下格式输出，每段用标签开头：\n"
                "分析结果：xxx\n\n方案对比：xxx\n\n操作建议：xxx\n"
                "禁止使用 ** # ` 等 Markdown 符号。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"【{urgency}】\n"
                f"钱包: {pos['wallet']}\n"
                f"健康度: {pos['health']:.4f}\n"
                f"总抵押: ${pos['collateral']:,.2f}\n"
                f"总借款: ${pos['debt']:,.2f}\n"
                f"{token_lines}{weighted_liq}\n"
                "请根据以上质押明细，判断是否需要补仓，并给出建议。"
            ),
        },
    ]
    # Build per-user model string with provider prefix
    _prefix_map = {"deepseek": "deepseek/", "gemini": "gemini/", "doubao": "volcengine/"}
    _prefix = _prefix_map.get(ai_provider, "")
    _model = ai_model
    if _prefix and _model and not _model.startswith(_prefix):
        _model = _prefix + _model
    try:
        return run_agent(messages, model=_model or None, api_key=ai_api_key or None)
    except Exception as e:
        err = str(e).lower()
        if any(k in err for k in ("quota", "insufficient_quota", "billing", "rate limit", "rate_limit", "429", "credit")):
            raise RuntimeError("__AI_QUOTA__") from e
        raise


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 单个地址检查（在 executor 里同步执行）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _check_address_sync(user: dict, address: str) -> None:
    user_wallet  = user["wallet_address"]
    rpc_url      = user.get("rpc_url") or None
    chat_id      = user.get("telegram_chat_id", "")
    cooldown_w   = user.get("alert_cooldown_warning", 30)
    cooldown_d   = user.get("alert_cooldown_danger", 5)
    use_custom   = user.get("custom_thresholds", False)
    custom_warn  = user.get("warning_hf", 1.4)
    custom_danger= user.get("danger_hf", 1.1)
    ai_provider  = user.get("ai_provider", "")
    ai_model     = user.get("ai_model", "")
    ai_api_key   = user.get("ai_api_key", "")

    short = address[:8] + "..."
    try:
        pos = get_position(address, rpc_url)
    except Exception as e:
        print(f"    [{short}] 查询失败: {e}")
        print(traceback.format_exc())
        return

    if pos["debt"] == 0 or pos["health"] > 1e10:
        print(f"    [{short}] 无借款，跳过")
        return

    # 获取质押明细以计算加权阈值
    try:
        breakdown = get_user_collateral_breakdown(address, rpc_url)
    except Exception:
        print(traceback.format_exc())
        breakdown = {}

    if use_custom:
        alert_t, danger_t = custom_warn, custom_danger
    else:
        alert_t, danger_t = compute_weighted_thresholds(breakdown)

    level = _alert_level(pos["health"], alert_t, danger_t)
    now   = datetime.now().strftime("%H:%M:%S")
    print(f"    [{now}] [{short}] {_level_emoji(level)}  HF={pos['health']:.4f}  (阈值={alert_t})")

    # 写健康历史（最多每 300s 一条，避免数据库膨胀）
    hist_key = (user_wallet, address)
    last_write = _last_history_write.get(hist_key)
    if not last_write or (datetime.now() - last_write).total_seconds() >= HISTORY_INTERVAL:
        _write_health_history(user_wallet, address, pos, level)
        _last_history_write[hist_key] = datetime.now()

    if level == "SAFE":
        return

    key = (user_wallet, address)
    if not _should_alert(key, level, cooldown_w, cooldown_d):
        return

    _last_alert[key] = {"level": level, "time": datetime.now()}

    print(f"\n    {'!'*50}")
    print(f"    {_level_emoji(level)} 告警  —  用户: {user_wallet[:8]}...  地址: {short}")
    print(f"    HF={pos['health']:.4f}  告警阈值={alert_t}  紧急阈值={danger_t}")
    advice = ""
    if not ai_api_key:
        print(f"    [AI] 用户未配置 API Key，跳过分析")
    elif user_wallet in _ai_quota_alerted:
        print(f"    [AI] 余额不足（已通知），跳过 AI 分析")
    else:
        print(f"    AI 分析中...")
        with _ai_lock:
            try:
                advice = _ai_analysis(pos, level, breakdown, ai_provider, ai_model, ai_api_key)
                _ai_quota_alerted.discard(user_wallet)
                print(f"    AI 建议: {advice}")
            except Exception as e:
                if "__AI_QUOTA__" in str(e):
                    print(f"    [AI] 余额不足，发送提示后降级")
                    _ai_quota_alerted.add(user_wallet)
                    _send_telegram(
                        chat_id,
                        "⚠️ <b>AI API Key 余额不足</b>\n"
                        "AI 分析功能已暂停，监控告警继续正常发送。\n"
                        "请前往对应平台充值后，AI 分析将自动恢复。"
                    )
                else:
                    print(f"    [AI] 分析失败: {e}")

    print(f"    {'!'*50}\n")

    _send_telegram(
        chat_id,
        f"{_level_emoji(level)} <b>{address[:10]}...</b>\n"
        f"健康度: {pos['health']:.4f}  (告警阈值: {alert_t})\n"
        f"抵押: ${pos['collateral']:,.2f}  |  借款: ${pos['debt']:,.2f}\n\n"
        + (advice if advice else "（AI 分析暂不可用）")
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 异步包装层
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_user(loop: asyncio.AbstractEventLoop, user: dict) -> None:
    """检查一个用户的所有监控地址（根据 refresh_interval 决定是否跳过）"""
    wallet         = user["wallet_address"]
    refresh        = user.get("refresh_interval", 300)
    addresses      = [a for a in (user.get("monitor_addresses") or []) if a.startswith("0x")]

    last = _last_check.get(wallet)
    if last and (datetime.now() - last).total_seconds() < refresh:
        return   # 还没到该用户的刷新时间

    if not addresses:
        return

    _last_check[wallet] = datetime.now()
    print(f"  [用户 {wallet[:8]}...] 检查 {len(addresses)} 个地址")

    tasks = [
        loop.run_in_executor(None, _check_address_sync, user, addr)
        for addr in addresses
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 主循环
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def run_monitor() -> None:
    loop = asyncio.get_event_loop()

    print(f"\n{'='*55}")
    print(f"  Liquidation Guard 多用户监控启动")
    print(f"  主循环间隔: {POLL_INTERVAL} 秒")
    print(f"  Telegram Bot: {'已配置' if TELEGRAM_TOKEN else '未配置'}")
    print(f"{'='*55}\n")

    round_num = 0
    last_cleanup = datetime.now()
    while True:
        round_num += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[第 {round_num} 轮] {now}")

        # 每天清理一次旧历史
        if (datetime.now() - last_cleanup).total_seconds() > 86400:
            await loop.run_in_executor(None, _cleanup_old_history)
            last_cleanup = datetime.now()

        # 每轮重新拉取用户列表（支持用户实时开关监控）
        users = await loop.run_in_executor(None, _fetch_users)

        if not users:
            print("  暂无启用监控的用户")
        else:
            print(f"  活跃用户数: {len(users)}")
            await asyncio.gather(
                *[check_user(loop, u) for u in users],
                return_exceptions=True,
            )

        print(f"  等待 {POLL_INTERVAL} 秒...\n")
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(run_monitor())
    except KeyboardInterrupt:
        print("\n监控已停止（Ctrl+C）")
