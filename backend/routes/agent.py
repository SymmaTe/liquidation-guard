"""
Agent 对话接口：
POST /agent/chat  — 前端传入消息历史 + 用户 API Key，后端跑 Tool Use 返回回复
"""

import asyncio
import json
import os
import sys
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

# 把 agent/ 目录加入 import 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agent")))

from db import supabase
from crypto import decrypt
from litellm import acompletion
from read_position import (
    get_position,
    get_token_price,
    get_token_ltv,
    get_user_collateral_breakdown,
)

router = APIRouter()

# ─── 系统提示 ──────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "你是 Liquidation Guard 的专属 AI 助手，具备两种能力：\n"
    "1. 通过工具实时查询 Aave V3 链上数据，分析仓位风险、计算补仓/还款方案\n"
    "2. 详细解答关于 Liquidation Guard 产品的所有问题（功能、配置、使用方法等）\n"
    "回答用中文，链上数据必须实时查询，不得估算。\n"
    "重要：产品使用、配置、注册教程类问题直接根据产品知识库回答，禁止调用任何工具。\n\n"

    "【查询仓位的标准流程 — 必须严格遵守】\n"
    "用户提供钱包地址后，无论有无借款，必须依次调用以下两个工具，缺一不可：\n"
    "1. get_aave_position — 获取总抵押、总借款、健康度\n"
    "2. get_collateral_breakdown — 获取每种质押代币的数量、USD价值、独立LTV和清算阈值\n"
    "即使用户只质押了单一代币，也必须调用 get_collateral_breakdown 来展示明细。\n"
    "禁止只调用其中一个就给出分析结论。\n\n"

    "【风险处置建议规则】\n"
    "健康度不足时，有两种方案，需同时给出并比较：\n"
    "方案A — 还款：调用 calculate_repayment_needed，直接降低债务，通常更高效\n"
    "  - 若借了稳定币，直接还稳定币即可\n"
    "  - 若借了 ETH/WBTC 等波动资产，ETH 涨价会让债务变大，优先还掉更安全\n"
    "方案B — 补仓：调用 calculate_collateral_needed（传入加权清算阈值）\n"
    "  - 稳定币（USDC/USDT/DAI）价格不跌，适合保守用户\n"
    "  - ETH/WBTC 清算阈值高，补仓效率更高\n"
    "  - LINK/AAVE 清算阈值低，不优先推荐\n"
    "最终建议说明哪种方案更划算，用户自行选择。\n\n"

    "【产品知识库】\n\n"

    "## 产品概览\n"
    "Liquidation Guard 是一个 Aave V3 仓位监控与保护工具，面向以太坊主网。\n"
    "四大核心功能：仓位总览 / 压力测试 / 自动监控告警 / AI 对话分析\n\n"

    "## 仓位页（/position）\n"
    "- 连接钱包后自动加载当前钱包的 Aave V3 仓位\n"
    "- 也可手动输入任意以太坊地址查询他人仓位\n"
    "- 显示：总抵押（USD）、总借款（USD）、健康度（HF）、净资产\n"
    "- 显示每种质押代币的数量、USD价值、LTV、清算阈值\n"
    "- 显示每种借款代币的数量、USD价值\n"
    "- 健康度颜色：绿色 ≥1.4（安全）/ 黄色 ≥1.1（注意）/ 红色 <1.1（危险）\n"
    "- 压力测试：拖动滑块模拟 ETH/BTC 价格下跌，实时预览健康度变化\n\n"

    "## 设置页（/settings）\n\n"
    "### RPC URL\n"
    "- 作用：连接以太坊主网节点，用于后端监控。填写后监控间隔可缩短至 30 秒；不填默认用公共节点（最快 5 分钟）\n"
    "- 如何获取（推荐 Alchemy）：\n"
    "  1. 访问 alchemy.com，点击右上角 Sign Up 注册免费账号\n"
    "  2. 登录后点击 Create new app，选择 Ethereum 主网（Mainnet）\n"
    "  3. 创建后进入 App 详情，点击 API Key，复制 HTTPS 格式的 URL\n"
    "  4. URL 格式：https://eth-mainnet.g.alchemy.com/v2/你的Key\n"
    "  5. 将该 URL 粘贴到设置页 RPC URL 输入框，点击「测试连接」验证\n"
    "- 也可使用 Infura（infura.io）：注册后创建 Ethereum 项目，复制 HTTPS endpoint\n"
    "- 免费额度：Alchemy 每天 3 亿计算单元（CU），监控使用量极少，完全够用\n\n"
    "### 监控地址\n"
    "- 最多添加 2 个以太坊地址（不限于自己的钱包），全部纳入监控\n"
    "- 每个地址独立监控，任意一个触发阈值都会发 Telegram 告警\n\n"
    "### 检查间隔\n"
    "- 无 RPC URL：最快 5 分钟检查一次\n"
    "- 有 RPC URL：最快 30 秒检查一次（适合激进仓位）\n\n"
    "### 告警阈值\n"
    "- 默认使用动态加权阈值（根据质押组合自动计算，更精准）\n"
    "- 也可手动设置注意线和紧急线 HF 值\n"
    "- 告警冷却：WARNING 默认 30 分钟内不重复发，DANGER 默认 5 分钟内不重复发\n"
    "- 级别升级（WARNING→DANGER）立即触发，不受冷却限制\n\n"
    "### Telegram 告警配置\n"
    "- 需要填写：Telegram Chat ID\n"
    "- 如何获取 Chat ID：\n"
    "  1. 在 Telegram 搜索 @userinfobot，点击 Start\n"
    "  2. 它会回复你的 User ID，这就是你的 Chat ID（数字，可能是负数表示群组）\n"
    "  3. 将该数字填入设置页 Telegram Chat ID 输入框\n"
    "  4. 点击「发送测试消息」验证是否能收到\n"
    "- 告警消息包含：健康度、告警级别、抵押/借款金额、AI 分析建议\n\n"
    "### AI 配置\n"
    "- 支持 5 个提供商：Anthropic（Claude）/ OpenAI（GPT）/ Google（Gemini）/ DeepSeek / 豆包\n"
    "- 需填入对应平台的 API Key，Key 安全存储于服务器，仅用于 AI 对话和监控告警\n"
    "- 如何获取 API Key 及常用模型 ID：\n"
    "  * Anthropic Claude：console.anthropic.com → API Keys\n"
    "    模型 ID：claude-opus-4-6 / claude-sonnet-4-6 / claude-haiku-4-5-20251001\n"
    "  * OpenAI：platform.openai.com → API Keys\n"
    "    模型 ID：gpt-4o / gpt-4o-mini / o3-mini\n"
    "  * Google Gemini：aistudio.google.com → Get API Key\n"
    "    模型 ID：gemini-2.0-flash / gemini-1.5-pro / gemini-1.5-flash\n"
    "  * DeepSeek：platform.deepseek.com → API Keys\n"
    "    模型 ID：deepseek-chat / deepseek-reasoner\n"
    "  * 豆包：console.volcengine.com → 模型推理 → API Key\n"
    "    模型 ID 需要日期后缀，示例：doubao-pro-32k-241215 / doubao-pro-128k-241215 / doubao-seed-2-0-pro-260215\n"
    "    （日期后缀因版本而异，请在火山引擎控制台「模型推理 → 模型广场」查看当前可用的完整 ID）\n"
    "- 点击「测试 AI 连接」可验证 Key 是否有效（5 秒超时）\n\n"

    "## 自动监控工作原理\n"
    "- 后端每 10 秒扫描一次所有开启监控的用户\n"
    "- 根据每个用户设置的检查间隔决定是否实际查询链上数据\n"
    "- 查询到的健康度每 5 分钟写入一次数据库（用于历史图表，控制存储量）\n"
    "- 健康度低于阈值时：调用 AI 分析 → 通过 Telegram 发送告警 + AI 建议\n"
    "- 若 AI API Key 余额不足：告警照常发送，仅 AI 分析部分暂停（会有一次性充值提示）\n\n"

    "## 常见问题\n"
    "Q：为什么没收到 Telegram 告警？\n"
    "A：请检查：① 设置页监控开关是否打开 ② Telegram Chat ID 是否正确 ③ 点击测试按钮是否能收到消息 ④ 健康度是否真的低于阈值\n\n"
    "Q：健康度为什么一直不变？\n"
    "A：若无借款，健康度显示为 ∞（无限大），这是正常的。有借款时健康度随代币价格实时波动。\n\n"
    "Q：RPC URL 填了但测试失败？\n"
    "A：确认 URL 是 HTTPS 格式，网络不是 Ethereum 测试网，Key 未过期或达到限额。\n\n"
    "Q：AI 对话响应很慢？\n"
    "A：AI 需要调用工具查询链上数据，通常需要 10-30 秒，属于正常现象。\n\n"
    "Q：支持哪些代币？\n"
    "A：支持 Aave V3 主网所有代币，包括 ETH、WBTC、USDC、USDT、DAI、LINK、AAVE、wstETH 等。\n\n"
    "Q：数据安全吗？AI Key 会泄露吗？\n"
    "A：AI Key 经加密后存储于服务器，前端无法读取明文，日志中也不会出现。链上查询通过你自己的 RPC URL 进行。\n"
)

# ─── 工具定义 ──────────────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_aave_position",
            "description": "查询某个钱包地址在 Aave V3 上的借贷仓位，返回抵押价值、借款金额、健康度等数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_address": {"type": "string", "description": "以太坊钱包地址（0x 开头）"}
                },
                "required": ["wallet_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_token_price",
            "description": "从 Chainlink 链上预言机获取代币实时 USD 价格。支持：ETH、WBTC、USDC、USDT、DAI、LINK、AAVE、WSTETH。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "代币符号，大写，例如 ETH"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_token_ltv",
            "description": "查询代币在 Aave V3 上的 LTV 和清算阈值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "代币符号，大写"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_collateral_breakdown",
            "description": "查询用户在 Aave V3 上的质押和借款明细（数量、USD价值、LTV、清算阈值）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_address": {"type": "string", "description": "以太坊钱包地址"}
                },
                "required": ["wallet_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_repayment_needed",
            "description": "计算要让健康度恢复到目标值，需要还多少借款代币。",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_collateral_usd": {"type": "number"},
                    "current_debt_usd":       {"type": "number"},
                    "liq_threshold":          {"type": "number"},
                    "token_price_usd":        {"type": "number"},
                    "target_health":          {"type": "number"},
                },
                "required": ["current_collateral_usd", "current_debt_usd", "liq_threshold", "token_price_usd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_collateral_needed",
            "description": "计算要让健康度恢复到目标值，需要额外补充多少代币作为抵押。",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_collateral_usd": {"type": "number"},
                    "current_debt_usd":       {"type": "number"},
                    "liq_threshold":          {"type": "number"},
                    "token_price_usd":        {"type": "number"},
                    "target_health":          {"type": "number"},
                },
                "required": ["current_collateral_usd", "current_debt_usd", "liq_threshold", "token_price_usd"],
            },
        },
    },
]


# ─── 工具执行 ──────────────────────────────────────────────────────────────────
def _calculate_repayment_needed(
    current_collateral_usd: float, current_debt_usd: float,
    liq_threshold: float, token_price_usd: float, target_health: float = 1.5,
) -> dict:
    target_debt  = (current_collateral_usd * liq_threshold) / target_health
    repay_usd    = max(0, current_debt_usd - target_debt)
    tokens       = repay_usd / token_price_usd if token_price_usd > 0 else 0
    current_hf   = (current_collateral_usd * liq_threshold) / current_debt_usd if current_debt_usd > 0 else 0
    return {
        "current_health": round(current_hf, 4),
        "target_health":  target_health,
        "repay_usd":      round(repay_usd, 2),
        "tokens_to_repay": round(tokens, 6),
        "summary": f"需还约 {tokens:.4f} 个代币（${repay_usd:,.2f}）可达健康度 {target_health}",
    }


def _calculate_collateral_needed(
    current_collateral_usd: float, current_debt_usd: float,
    liq_threshold: float, token_price_usd: float, target_health: float = 1.5,
) -> dict:
    target_col   = (current_debt_usd * target_health) / liq_threshold
    shortfall    = max(0, target_col - current_collateral_usd)
    tokens       = shortfall / token_price_usd if token_price_usd > 0 else 0
    current_hf   = (current_collateral_usd * liq_threshold) / current_debt_usd if current_debt_usd > 0 else 0
    return {
        "current_health": round(current_hf, 4),
        "target_health":  target_health,
        "shortfall_usd":  round(shortfall, 2),
        "tokens_needed":  round(tokens, 6),
        "summary": f"需补约 {tokens:.4f} 个代币（${shortfall:,.2f}）可达健康度 {target_health}",
    }


def _execute_tool(name: str, args: dict, rpc_url: str | None) -> str:
    try:
        if name == "get_aave_position":
            pos = get_position(args["wallet_address"], rpc_url)
            result = {"status": "no_debt", **pos} if pos["health"] > 1e10 else pos
        elif name == "get_token_price":
            result = get_token_price(args["symbol"], rpc_url)
        elif name == "get_token_ltv":
            result = get_token_ltv(args["symbol"], rpc_url)
        elif name == "get_collateral_breakdown":
            result = get_user_collateral_breakdown(args["wallet_address"], rpc_url)
        elif name == "calculate_repayment_needed":
            result = _calculate_repayment_needed(**args)
        elif name == "calculate_collateral_needed":
            result = _calculate_collateral_needed(**args)
        else:
            result = {"error": f"未知工具: {name}"}
    except Exception as e:
        result = {"error": str(e)}
    return json.dumps(result, ensure_ascii=False)


# ─── 请求 / 响应模型 ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    messages:       list
    model:          str
    provider:       str = "anthropic"
    rpc_url:        Optional[str] = None
    wallet_address: Optional[str] = None


# ─── 接口 ──────────────────────────────────────────────────────────────────────
@router.post("/chat")
async def agent_chat(body: ChatRequest):
    async def generate():
        try:
            # Fetch user's API key and thresholds from DB
            api_key = ""
            warning_hf = 1.4
            if body.wallet_address:
                try:
                    res = supabase.table("user_settings").select("ai_api_key, warning_hf").eq("wallet_address", body.wallet_address).single().execute()
                    if res.data:
                        api_key = decrypt(res.data.get("ai_api_key") or "")
                        warning_hf = float(res.data.get("warning_hf") or 1.4)
                except Exception:
                    pass
            if not api_key:
                yield f"data: {json.dumps({'error': '请先在设置页配置 AI API Key'}, ensure_ascii=False)}\n\n"
                return

            messages = list(body.messages)

            if not messages or messages[0].get("role") != "system":
                system = SYSTEM_PROMPT
                if body.wallet_address:
                    target_hf = round(warning_hf + 0.05, 2)
                    system += (
                        f"\n\n【用户钱包地址】{body.wallet_address}\n"
                        f"用户询问「我的仓位」时，直接用此地址查询，无需再索要。\n"
                        f"【用户告警阈值】警告线 HF={warning_hf}，计算补仓/还款时目标健康度统一使用 {target_hf}（警告线 + 0.05 最小缓冲），"
                        f"调用 calculate_repayment_needed 和 calculate_collateral_needed 时必须传入 target_health={target_hf}。"
                    )
                messages.insert(0, {"role": "system", "content": system})

            rpc_url = body.rpc_url or None
            model   = body.model
            prefix_map = {"deepseek": "deepseek/", "google": "gemini/", "doubao": "volcengine/"}
            prefix = prefix_map.get(body.provider, "")
            if prefix and not model.startswith(prefix):
                model = prefix + model

            loop = asyncio.get_event_loop()

            for _ in range(6):
                response = await acompletion(
                    model=model,
                    api_key=api_key,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=2000,
                    timeout=60,
                    stream=True,
                )

                collected_content = ""
                collected_tool_calls: dict[int, dict] = {}
                round_type = None  # 'text' | 'tool'

                async for chunk in response:
                    delta = chunk.choices[0].delta

                    # 第一个有效 delta 决定本轮类型
                    if round_type is None:
                        if delta.content:
                            round_type = "text"
                        elif delta.tool_calls:
                            round_type = "tool"

                    # 累积 tool_calls
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in collected_tool_calls:
                                collected_tool_calls[idx] = {
                                    "id": tc.id or "",
                                    "type": "function",
                                    "function": {"name": tc.function.name or "", "arguments": ""},
                                }
                            else:
                                if tc.id:
                                    collected_tool_calls[idx]["id"] = tc.id
                                if tc.function and tc.function.name:
                                    collected_tool_calls[idx]["function"]["name"] += tc.function.name
                                if tc.function and tc.function.arguments:
                                    collected_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

                    # 文字轮次实时 emit
                    if delta.content:
                        collected_content += delta.content
                        if round_type == "text":
                            yield f"data: {json.dumps({'text': delta.content}, ensure_ascii=False)}\n\n"

                if collected_tool_calls:
                    # 工具调用轮次：并行执行所有工具
                    tool_calls_list = [collected_tool_calls[i] for i in sorted(collected_tool_calls.keys())]
                    messages.append({
                        "role": "assistant",
                        "content": collected_content or None,
                        "tool_calls": tool_calls_list,
                    })
                    def _parse_args(raw: str) -> dict:
                        try:
                            return json.loads(raw) if raw else {}
                        except json.JSONDecodeError:
                            return {}
                    tool_results = await asyncio.gather(*[
                        loop.run_in_executor(
                            None, _execute_tool,
                            tc["function"]["name"],
                            _parse_args(tc["function"]["arguments"]),
                            rpc_url,
                        )
                        for tc in tool_calls_list
                    ])
                    for tc, result in zip(tool_calls_list, tool_results):
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                else:
                    # 文字轮次结束
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    return

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ("insufficient_quota", "exceeded your current quota", "billing", "you have run out", "no credits")):
                yield f"data: {json.dumps({'error': 'API Key 余额不足或超出限额，请前往对应平台充值后重试。'}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
