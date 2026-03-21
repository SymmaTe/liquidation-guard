"""
测试连接接口：
- POST /test/rpc       — 验证 RPC URL（eth_blockNumber，5 秒超时）
- POST /test/ai        — 验证 AI API Key + 模型 ID（5 秒超时）
- POST /test/telegram  — 发送测试消息到用户 Telegram Chat ID
"""

import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

FALLBACK_RPC = "https://eth.llamarpc.com"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


# ─── 请求体 ───────────────────────────────────────────────────────────────────

class RpcTestRequest(BaseModel):
    rpc_url: str

class AiTestRequest(BaseModel):
    provider: str   # anthropic | openai | google | deepseek | doubao
    api_key: str
    model: str

class TelegramTestRequest(BaseModel):
    chat_id: str


# ─── RPC 测试 ─────────────────────────────────────────────────────────────────

@router.post("/rpc")
async def test_rpc(body: RpcTestRequest):
    url = body.rpc_url.strip() or FALLBACK_RPC
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
        if "result" in data:
            block = int(data["result"], 16)
            return {"ok": True, "block": block}
        return {"ok": False, "error": data.get("error", {}).get("message", "未知错误")}
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接超时（5 秒），请检查 RPC URL 是否正确"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── AI 测试 ──────────────────────────────────────────────────────────────────

AI_ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai":    "https://api.openai.com/v1/chat/completions",
    "google":    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "deepseek":  "https://api.deepseek.com/v1/chat/completions",
    "doubao":    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
}

@router.post("/ai")
async def test_ai(body: AiTestRequest):
    provider = body.provider.lower()
    if provider not in AI_ENDPOINTS:
        return {"ok": False, "error": f"不支持的提供商: {provider}"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if provider == "anthropic":
                resp = await client.post(
                    AI_ENDPOINTS["anthropic"],
                    headers={"x-api-key": body.api_key, "anthropic-version": "2023-06-01"},
                    json={"model": body.model, "max_tokens": 1,
                          "messages": [{"role": "user", "content": "hi"}]},
                )
            elif provider == "google":
                url = AI_ENDPOINTS["google"].format(model=body.model)
                resp = await client.post(
                    f"{url}?key={body.api_key}",
                    json={"contents": [{"parts": [{"text": "hi"}]}]},
                )
            else:
                # OpenAI 兼容接口（openai / deepseek / doubao）
                resp = await client.post(
                    AI_ENDPOINTS[provider],
                    headers={"Authorization": f"Bearer {body.api_key}"},
                    json={"model": body.model, "max_tokens": 1,
                          "messages": [{"role": "user", "content": "hi"}]},
                )

        # 判断结果：400 以下基本都是 key/model 问题而非网络问题
        if resp.status_code < 500:
            # 401 = key 错误，404 = model 不存在，200/400 = 连通
            if resp.status_code == 401:
                return {"ok": False, "error": "API Key 无效或已过期"}
            if resp.status_code == 404:
                return {"ok": False, "error": f"模型 ID「{body.model}」不存在，请检查官方文档"}
            return {"ok": True, "message": f"连接成功（HTTP {resp.status_code}）"}
        return {"ok": False, "error": f"服务端错误 HTTP {resp.status_code}"}

    except httpx.TimeoutException:
        return {"ok": False, "error": "连接超时（5 秒），请检查网络或 API 地址"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Telegram 测试 ───────────────────────────────────────────────────────────

@router.post("/telegram")
async def test_telegram(body: TelegramTestRequest):
    if not TELEGRAM_BOT_TOKEN:
        return {"ok": False, "error": "后端未配置 TELEGRAM_BOT_TOKEN"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": body.chat_id,
        "text": "✅ Liquidation Guard 连接成功！你将在仓位风险时收到此类通知。",
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
        if data.get("ok"):
            return {"ok": True, "message": "测试消息已发送，请检查 Telegram"}
        return {"ok": False, "error": data.get("description", "发送失败")}
    except httpx.TimeoutException:
        return {"ok": False, "error": "连接超时（5 秒）"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
