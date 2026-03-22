"""
Step 4: Tool Use — AI Agent 核心
- 给 AI 定义可调用的工具
- AI 自己决定什么时候调用哪个工具、传什么参数
- 实现多轮对话，用户可以追问

所有链上数据读取逻辑在 read_position.py
"""

import json
from litellm import completion
from dotenv import load_dotenv
import os
import sys
sys.path.append(".")
from read_position import (
    get_position,
    get_token_price,
    get_token_ltv,
    get_user_collateral_breakdown,
    print_position,
)

load_dotenv("../.env")

MODEL    = os.getenv("AI_MODEL", "ollama/llama3.2")
PROVIDER = os.getenv("AI_PROVIDER", "ollama")
_PREFIX_MAP = {"deepseek": "deepseek/", "gemini": "gemini/", "doubao": "volcengine/"}
_prefix = _PREFIX_MAP.get(PROVIDER, "")
if _prefix and not MODEL.startswith(_prefix):
    MODEL = _prefix + MODEL
KEY_MAP  = {
    "anthropic": os.getenv("ANTHROPIC_API_KEY"),
    "openai":    os.getenv("OPENAI_API_KEY"),
    "gemini":    os.getenv("GEMINI_API_KEY"),
    "deepseek":  os.getenv("DEEPSEEK_API_KEY"),
    "doubao":    os.getenv("ARK_API_KEY"),
    "ollama":    "ollama",
}
API_KEY = KEY_MAP.get(PROVIDER, "ollama")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工具说明书（给 AI 看）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_aave_position",
            "description": "查询某个钱包地址在 Aave V3 上的借贷仓位，返回抵押价值、借款金额、健康度等数据。当用户提供钱包地址并询问仓位状态时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_address": {
                        "type": "string",
                        "description": "以太坊钱包地址，格式为 0x 开头的 42 位十六进制字符串",
                    }
                },
                "required": ["wallet_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_token_price",
            "description": "从 Chainlink 链上预言机获取代币的实时 USD 价格。当需要知道某个代币当前价格，或者计算补仓/还款需要多少代币时调用。支持：ETH、WBTC、USDC、USDT、DAI、LINK、AAVE、WSTETH。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "代币符号，大写，例如 ETH、WBTC、USDC",
                    }
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_token_ltv",
            "description": "查询某个代币在 Aave V3 上的 LTV（最高借款比例）和清算阈值。当用户询问某代币能借多少、或者需要计算补仓数量时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "代币符号，大写，例如 ETH、WBTC",
                    }
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_collateral_breakdown",
            "description": "查询用户在 Aave V3 上的质押和借款明细：质押代币（数量、USD 价值、LTV、清算阈值）、借款代币（数量、USD 价值）、加权清算阈值。当用户询问具体质押/借了哪些代币、或需要计算补仓/还款方案时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "wallet_address": {
                        "type": "string",
                        "description": "以太坊钱包地址",
                    }
                },
                "required": ["wallet_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_repayment_needed",
            "description": "计算要让健康度恢复到目标值，需要还多少某种借款代币。当用户问'我要还多少才安全'或'还款方案'时调用。还款直接降低债务，通常比补仓更高效。",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_collateral_usd": {
                        "type": "number",
                        "description": "当前总抵押价值（USD）",
                    },
                    "current_debt_usd": {
                        "type": "number",
                        "description": "当前总借款金额（USD）",
                    },
                    "liq_threshold": {
                        "type": "number",
                        "description": "清算阈值，小数形式，例如 0.825",
                    },
                    "token_price_usd": {
                        "type": "number",
                        "description": "要偿还的代币当前价格（USD）",
                    },
                    "target_health": {
                        "type": "number",
                        "description": "目标健康度，默认 1.5",
                    },
                },
                "required": ["current_collateral_usd", "current_debt_usd", "liq_threshold", "token_price_usd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_collateral_needed",
            "description": "计算要让健康度恢复到目标值，需要额外补充多少某种代币作为抵押。当用户问'我要补多少ETH'或'补仓多少才安全'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_collateral_usd": {
                        "type": "number",
                        "description": "当前总抵押价值（USD）",
                    },
                    "current_debt_usd": {
                        "type": "number",
                        "description": "当前总借款金额（USD）",
                    },
                    "liq_threshold": {
                        "type": "number",
                        "description": "清算阈值，小数形式，例如 0.825",
                    },
                    "token_price_usd": {
                        "type": "number",
                        "description": "要补充的代币当前价格（USD）",
                    },
                    "target_health": {
                        "type": "number",
                        "description": "目标健康度，默认 1.5",
                    },
                },
                "required": ["current_collateral_usd", "current_debt_usd", "liq_threshold", "token_price_usd"],
            },
        },
    },
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工具实现（纯业务逻辑，无 web3）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_aave_position(wallet_address: str) -> dict:
    """调用 read_position 查询链上仓位"""
    try:
        pos = get_position(wallet_address)
        if pos["health"] > 1e10:
            return {"status": "no_debt", "wallet": wallet_address, "collateral": pos["collateral"]}
        return pos
    except Exception as e:
        return {"error": f"查询失败：{str(e)}"}


def calculate_repayment_needed(
    current_collateral_usd: float,
    current_debt_usd: float,
    liq_threshold: float,
    token_price_usd: float,
    target_health: float = 1.5,
) -> dict:
    """
    计算还款数量
    目标债务 = 总抵押 × 清算阈值 / 目标健康度
    需还 USD = 当前债务 - 目标债务
    需还数量 = 需还 USD / 代币价格
    """
    target_debt_usd   = (current_collateral_usd * liq_threshold) / target_health
    repay_usd         = max(0, current_debt_usd - target_debt_usd)
    tokens_to_repay   = repay_usd / token_price_usd if token_price_usd > 0 else 0
    current_health    = (current_collateral_usd * liq_threshold) / current_debt_usd if current_debt_usd > 0 else 0

    return {
        "current_health":    round(current_health, 4),
        "target_health":     target_health,
        "current_debt_usd":  current_debt_usd,
        "target_debt_usd":   round(target_debt_usd, 2),
        "repay_usd":         round(repay_usd, 2),
        "token_price_usd":   token_price_usd,
        "tokens_to_repay":   round(tokens_to_repay, 6),
        "summary": f"当前健康度 {current_health:.2f}，需还约 {tokens_to_repay:.4f} 个代币（价值 ${repay_usd:,.2f}）可达到健康度 {target_health}",
    }


def calculate_collateral_needed(
    current_collateral_usd: float,
    current_debt_usd: float,
    liq_threshold: float,
    token_price_usd: float,
    target_health: float = 1.5,
) -> dict:
    """
    计算补仓数量
    目标抵押 = 借款 × 目标健康度 / 清算阈值
    缺口 USD  = 目标抵押 - 当前抵押
    需要数量  = 缺口 USD / 代币价格
    """
    target_collateral_usd = (current_debt_usd * target_health) / liq_threshold
    shortfall_usd  = max(0, target_collateral_usd - current_collateral_usd)
    tokens_needed  = shortfall_usd / token_price_usd if token_price_usd > 0 else 0
    current_health = (current_collateral_usd * liq_threshold) / current_debt_usd if current_debt_usd > 0 else 0

    return {
        "current_health":         round(current_health, 4),
        "target_health":          target_health,
        "current_collateral_usd": current_collateral_usd,
        "target_collateral_usd":  round(target_collateral_usd, 2),
        "shortfall_usd":          round(shortfall_usd, 2),
        "token_price_usd":        token_price_usd,
        "tokens_needed":          round(tokens_needed, 6),
        "summary": f"当前健康度 {current_health:.2f}，需补充约 {tokens_needed:.4f} 个代币（价值 ${shortfall_usd:,.2f}）可达到健康度 {target_health}",
    }


def execute_tool(tool_name: str, tool_args: dict) -> str:
    """根据 AI 决定执行对应工具，返回 JSON 字符串"""
    dispatch = {
        "get_aave_position":           get_aave_position,
        "get_token_price":             get_token_price,
        "get_token_ltv":               get_token_ltv,
        "get_collateral_breakdown":    get_user_collateral_breakdown,
        "calculate_repayment_needed":  calculate_repayment_needed,
        "calculate_collateral_needed": calculate_collateral_needed,
    }
    fn = dispatch.get(tool_name)
    result = fn(**tool_args) if fn else {"error": f"未知工具: {tool_name}"}
    return json.dumps(result, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent 主循环
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_agent(messages: list) -> str:
    pos_result = None
    bd_result  = None

    for _ in range(6):
        response = completion(
            model=MODEL,
            api_key=API_KEY,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=512,
            timeout=30,
        )
        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})
            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                print(f"\n  [Agent 调用工具] {tool_name}({tool_args})")
                result = execute_tool(tool_name, tool_args)
                print(f"  [工具返回] {result[:120]}...")
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      result,
                })
                parsed = json.loads(result)
                if tool_name == "get_aave_position" and "error" not in parsed:
                    pos_result = parsed
                elif tool_name == "get_collateral_breakdown" and "error" not in parsed:
                    bd_result = parsed

            if pos_result and bd_result and "health" in pos_result:
                print()
                print_position(pos_result, bd_result)
                pos_result = None  # 展示后重置，避免多轮对话重复打印
                bd_result  = None
        else:
            return msg.content


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 多轮对话入口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def chat():
    print(f"\n{'='*55}")
    print("  Liquidation Guard AI Agent")
    print(f"  模型：{MODEL}")
    print(f"  输入 'quit' 退出")
    print(f"{'='*55}\n")

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个专业的 DeFi 风险分析 Agent，帮助用户监控和保护 Aave V3 借贷仓位。\n\n"

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
                "  - ETH/WBTC 清算阈值高，补仓效率更高，适合有持仓意愿的用户\n"
                "  - LINK/AAVE 清算阈值低，补仓效率最低，不优先推荐\n"
                "最终建议说明哪种方案更划算，用户自行选择。\n\n"

                "所有价格和链上数据必须实时查询，不得使用估算值。回答用中文，简洁专业。"
            ),
        }
    ]

    while True:
        user_input = input("\n你：").strip()
        if not user_input or user_input.lower() == "quit":
            print("再见！")
            break

        messages.append({"role": "user", "content": user_input})
        print("\nAgent 思考中...", end="", flush=True)
        reply = run_agent(messages)
        print(f"\n\nAgent：{reply}")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    chat()
