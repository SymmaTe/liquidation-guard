"""
Step 3: AI 仓位风险分析器
- 使用 LiteLLM 统一接口，支持 Ollama / Anthropic / OpenAI / Gemini
- 读取仓位数据，让 AI 用中文生成风险报告和操作建议
"""

from litellm import completion
from dotenv import load_dotenv
import os
import sys
sys.path.append(".")
from read_position import print_position, compute_weighted_thresholds

load_dotenv("../.env")

# ── 从 .env 读取用户配置的模型 ────────────────────────
MODEL    = os.getenv("AI_MODEL", "ollama/llama3.2")
PROVIDER = os.getenv("AI_PROVIDER", "ollama")

# 根据 provider 选对应的 key，避免把 Claude key 发给 DeepSeek
KEY_MAP = {
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "openai":    os.getenv("OPENAI_API_KEY"),
    "gemini":    os.getenv("GEMINI_API_KEY"),
    "deepseek":  os.getenv("DEEPSEEK_API_KEY"),
    "ollama":    "ollama",  # 本地不需要真实 key
}
API_KEY = KEY_MAP.get(PROVIDER, "ollama")


def analyze_position(pos: dict, breakdown: dict = None) -> str:
    """
    把仓位数据传给 AI，返回中文风险分析报告。

    pos      — get_position() 或 mock_position() 返回的字典（总览）
    breakdown — get_user_collateral_breakdown() 或 mock_collateral_breakdown()
                返回的混合质押明细（可选）。有 breakdown 时，AI 能给出更精确的建议。
    """

    drop_to_liquidation = (1 - 1.0 / pos["health"]) * 100 if pos["health"] > 0 else 0

    alert_t, danger_t = compute_weighted_thresholds(breakdown) if breakdown else (1.4, 1.1)

    # ── 基础仓位部分 ──────────────────────────────────────
    prompt = f"""你是一个 DeFi 风险分析专家。请分析以下 Aave V3 借贷仓位，并给出中文报告。

## 仓位概览
- 钱包地址：{pos['wallet']}
- 总抵押价值：${pos['collateral']:,.2f} USD
- 总借款金额：${pos['debt']:,.2f} USD
- 健康度（Health Factor）：{pos['health']:.4f}
- 加权清算阈值：{pos['liq_threshold']:.0%}
- 距清算还有：约 {drop_to_liquidation:.1f}% 的下跌空间
"""

    # ── 质押明细 ──────────────────────────────────────────
    if breakdown and breakdown.get("collateral_tokens"):
        prompt += "\n## 质押代币明细\n"
        for t in breakdown["collateral_tokens"]:
            prompt += (
                f"- {t['symbol']}：{t['amount']} 个"
                f"  @ ${t['price_usd']:,.2f}"
                f"  = ${t['value_usd']:,.2f} USD"
                f"  （LTV {t['ltv_pct']}，清算阈值 {t['liq_threshold_pct']}）\n"
            )
        prompt += f"- 加权清算阈值：{breakdown['weighted_liq_pct']}\n"

    # ── 借款明细 ──────────────────────────────────────────
    if breakdown and breakdown.get("borrow_tokens"):
        prompt += "\n## 借款代币明细\n"
        for b in breakdown["borrow_tokens"]:
            prompt += (
                f"- {b['symbol']}：{b['amount']} 个"
                f"  @ ${b['price_usd']:,.2f}"
                f"  = ${b['value_usd']:,.2f} USD\n"
            )
        prompt += (
            "注意：若借出的是波动资产（如 ETH/WBTC），价格上涨会导致债务 USD 价值增加，"
            "健康度同样会下跌。\n"
        )

    # ── 健康度说明 + 输出格式 ─────────────────────────────
    prompt += """
## 健康度说明（基于当前质押/借款代币组成的动态阈值）
- ≥ {alert_t}：安全，有足够缓冲
- {danger_t} ~ {alert_t}：注意，需要关注
- < {danger_t}：危险，接近清算

## 请按以下格式输出报告（不超过200字）：
**风险等级**：（安全/注意/危险）
**当前状况**：（一句话描述仓位状态）
**风险预警**：（抵押品跌多少或借款涨多少会触发清算）
**建议操作**：（补仓或还款，说明哪种更划算；如有多种代币请分别说明优先级）
"""

    response = completion(
        model=MODEL,
        api_key=API_KEY,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )

    return response.choices[0].message.content


def print_analysis(pos: dict, breakdown: dict = None):
    """打印仓位数据 + AI 分析报告"""
    print_position(pos, breakdown)
    print(f"{'─'*55}")
    print("  AI 分析报告：")
    print()

    report = analyze_position(pos, breakdown)
    for line in report.strip().split("\n"):
        print(f"  {line}")

    print(f"{'='*55}")


if __name__ == "__main__":
    import sys
    sys.path.append(".")
    from read_position import mock_position, mock_collateral_breakdown

    print("正在连接 AI 模型，请稍候...\n")
    print(f"使用模型：{MODEL}\n")

    print("【场景一：单一质押 ETH，借 USDC，三种风险级别】")
    ETH_MOCK_PRICE = 2000.0
    for label, collateral, debt in [
        ("0xUser_Safe",    10000, 3000),
        ("0xUser_Warning", 10000, 6500),
        ("0xUser_Danger",  10000, 8500),
    ]:
        bd = mock_collateral_breakdown(
            label,
            tokens=[{"symbol": "ETH", "amount": collateral / ETH_MOCK_PRICE, "price_usd": ETH_MOCK_PRICE}],
            borrows=[{"symbol": "USDC", "amount": debt, "price_usd": 1.0}],
        )
        pos = mock_position(label, collateral=collateral, debt=debt,
                            liq_threshold=bd["weighted_liq_threshold"])
        print_analysis(pos, bd)

    print("\n【场景二：混合质押（ETH + WBTC + USDC），混合借款（USDT + ETH），警告级别】")
    breakdown = mock_collateral_breakdown(
        wallet="0xMixed_Warning",
        tokens=[
            {"symbol": "ETH",  "amount": 2.0,  "price_usd": 2000.0},
            {"symbol": "WBTC", "amount": 0.05, "price_usd": 60000.0},
            {"symbol": "USDC", "amount": 3000, "price_usd": 1.0},
        ],
        borrows=[
            {"symbol": "USDT", "amount": 5000, "price_usd": 1.0},
            {"symbol": "ETH",  "amount": 1.0,  "price_usd": 2000.0},   # 借了 ETH，涨价会压低 HF
        ],
    )
    pos_mixed = mock_position(
        wallet="0xMixed_Warning",
        collateral=breakdown["total_collateral_usd"],
        debt=7500,
        liq_threshold=breakdown["weighted_liq_threshold"],
    )
    print_analysis(pos_mixed, breakdown)
