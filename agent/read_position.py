"""
链上数据读取层 — 所有 Web3 / ABI 相关代码集中在这里
- Aave V3 仓位查询
- Chainlink 价格预言机
- Aave 代币配置（LTV、清算阈值）
"""

from web3 import Web3
from dotenv import load_dotenv
from functools import lru_cache
import os

load_dotenv("../.env")

FALLBACK_RPC = "https://eth.llamarpc.com"

@lru_cache(maxsize=32)
def _get_w3(rpc_url: str) -> Web3:
    """按 RPC URL 创建并缓存 Web3 实例，同一个 URL 只建一次连接"""
    return Web3(Web3.HTTPProvider(rpc_url))

def _get_contracts(rpc_url: str | None = None):
    """返回 (w3, pool, data_provider, wsteth_contract)"""
    url = rpc_url or os.getenv("MAINNET_RPC_URL") or FALLBACK_RPC
    w3 = _get_w3(url)
    pool = w3.eth.contract(address=AAVE_POOL, abi=AAVE_POOL_ABI)
    data_provider = w3.eth.contract(
        address=w3.to_checksum_address(AAVE_DATA_PROVIDER),
        abi=AAVE_DATA_PROVIDER_ABI,
    )
    wsteth_contract = w3.eth.contract(
        address=w3.to_checksum_address(WSTETH_ADDRESS),
        abi=WSTETH_ABI,
    )
    return w3, pool, data_provider, wsteth_contract


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Aave V3 Pool
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AAVE_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"

AAVE_POOL_ABI = [
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"name": "totalCollateralBase",         "type": "uint256"},  # 总抵押（USD，8位小数）
            {"name": "totalDebtBase",               "type": "uint256"},  # 总借款（USD，8位小数）
            {"name": "availableBorrowsBase",        "type": "uint256"},  # 还可借多少
            {"name": "currentLiquidationThreshold", "type": "uint256"},  # 清算阈值（basis points）
            {"name": "ltv",                         "type": "uint256"},  # 最大 LTV
            {"name": "healthFactor",                "type": "uint256"},  # 健康度（1e18 = 1.0）
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

AAVE_POOL_ABI.append({
    "inputs": [],
    "name": "getReservesList",
    "outputs": [{"name": "", "type": "address[]"}],
    "stateMutability": "view",
    "type": "function",
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Aave V3 Protocol Data Provider
# 用于查询每个代币的独立 LTV、清算阈值、用户余额
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AAVE_DATA_PROVIDER = "0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3"

AAVE_DATA_PROVIDER_ABI = [
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "user",  "type": "address"},
        ],
        "name": "getUserReserveData",
        "outputs": [
            {"name": "currentATokenBalance",    "type": "uint256"},  # 质押余额（原始单位）
            {"name": "currentStableDebt",       "type": "uint256"},
            {"name": "currentVariableDebt",     "type": "uint256"},
            {"name": "principalStableDebt",     "type": "uint256"},
            {"name": "scaledVariableDebt",      "type": "uint256"},
            {"name": "stableBorrowRate",        "type": "uint256"},
            {"name": "liquidityRate",           "type": "uint256"},
            {"name": "stableRateLastUpdated",   "type": "uint40"},
            {"name": "usageAsCollateralEnabled","type": "bool"},     # 是否启用为抵押
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "asset", "type": "address"}],
        "name": "getReserveConfigurationData",
        "outputs": [
            {"name": "decimals",                "type": "uint256"},
            {"name": "ltv",                     "type": "uint256"},  # basis points
            {"name": "liquidationThreshold",    "type": "uint256"},  # basis points
            {"name": "liquidationBonus",        "type": "uint256"},
            {"name": "reserveFactor",           "type": "uint256"},
            {"name": "usageAsCollateralEnabled","type": "bool"},
            {"name": "borrowingEnabled",        "type": "bool"},
            {"name": "stableBorrowRateEnabled", "type": "bool"},
            {"name": "isActive",                "type": "bool"},
            {"name": "isFrozen",                "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

# 代币合约地址 → symbol 映射（Aave V3 以太坊主网主要代币）
TOKEN_ADDRESS_TO_SYMBOL = {
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "ETH",
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": "WBTC",
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "USDC",
    "0xdAC17F958D2ee523a2206206994597C13D831ec7": "USDT",
    "0x6B175474E89094C44Da98b954EedeAC495271d0F": "DAI",
    "0x514910771AF9Ca656af840dff83E8264EcF986CA": "LINK",
    "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9": "AAVE",
    "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0": "WSTETH",
}

# symbol → 合约地址（反向映射，供链上查询用）
TOKEN_SYMBOL_TO_ADDRESS = {v: k for k, v in TOKEN_ADDRESS_TO_SYMBOL.items()}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Chainlink 价格预言机
# latestRoundData() 返回价格，8 位小数（除以 1e8）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHAINLINK_ABI = [{
    "inputs": [],
    "name": "latestRoundData",
    "outputs": [
        {"name": "roundId",         "type": "uint80"},
        {"name": "answer",          "type": "int256"},   # 价格，8位小数
        {"name": "startedAt",       "type": "uint256"},
        {"name": "updatedAt",       "type": "uint256"},
        {"name": "answeredInRound", "type": "uint80"},
    ],
    "stateMutability": "view",
    "type": "function",
}]

# 各代币 Chainlink 主网 Feed 地址（token/USD）
CHAINLINK_FEEDS = {
    "ETH":   "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
    "WBTC":  "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
    "USDC":  "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
    "USDT":  "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D",
    "DAI":   "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9",
    "LINK":  "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",
    "AAVE":  "0x547a514d5e3769680Ce22B2361c10Ea13619e8a9",
    # WSTETH 不直接用 Chainlink，由 get_token_price 单独计算
}

# wstETH 合约 ABI（只需 getStETHByWstETH，查 1 wstETH 对应多少 stETH）
WSTETH_ABI = [{
    "inputs": [{"name": "_wstETHAmount", "type": "uint256"}],
    "name": "getStETHByWstETH",
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function",
}]

WSTETH_ADDRESS  = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"
STETH_USD_FEED  = "0xCfE54B5cD566aB89272946F602D76Ea879CAb4a8"  # Chainlink stETH/USD


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Aave V3 代币配置（LTV、清算阈值）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 动态告警阈值（按代币波动性）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOKEN_THRESHOLDS = {
    "USDC":   {"alert": 1.2,  "danger": 1.05},
    "USDT":   {"alert": 1.2,  "danger": 1.05},
    "DAI":    {"alert": 1.2,  "danger": 1.05},
    "ETH":    {"alert": 1.4,  "danger": 1.1},
    "WBTC":   {"alert": 1.4,  "danger": 1.1},
    "WSTETH": {"alert": 1.4,  "danger": 1.1},
    "LINK":   {"alert": 1.4,  "danger": 1.1},
    "AAVE":   {"alert": 1.4,  "danger": 1.1},
}
_DEFAULT_THRESHOLDS = {"alert": 1.4, "danger": 1.1}


def compute_weighted_thresholds(breakdown: dict) -> tuple:
    """
    根据质押代币的价值占比加权计算告警阈值，同时考虑借款侧波动性（取两者最大值）。
    例：50% USDT (alert=1.2) + 50% ETH (alert=1.4) → 加权 alert=1.3
    若借了 ETH（波动资产），借款侧阈值也取 1.4，最终取 max。
    """
    def _weighted(tokens, total_value):
        if not tokens or total_value == 0:
            return _DEFAULT_THRESHOLDS["alert"], _DEFAULT_THRESHOLDS["danger"]
        wa, wd = 0.0, 0.0
        for t in tokens:
            w   = (t.get("value_usd") or 0) / total_value
            cfg = TOKEN_THRESHOLDS.get(t["symbol"], _DEFAULT_THRESHOLDS)
            wa += w * cfg["alert"]
            wd += w * cfg["danger"]
        return round(wa, 3), round(wd, 3)

    c_alert, c_danger = _weighted(
        breakdown.get("collateral_tokens", []),
        breakdown.get("total_collateral_usd", 0),
    )
    # 借款侧：以总抵押为分母做归一化，衡量借款波动对 HF 的影响权重
    total_col = breakdown.get("total_collateral_usd", 0)
    b_alert, b_danger = _weighted(
        breakdown.get("borrow_tokens", []),
        total_col,
    ) if total_col > 0 else (_DEFAULT_THRESHOLDS["alert"], _DEFAULT_THRESHOLDS["danger"])

    return max(c_alert, b_alert), max(c_danger, b_danger)


# 仅供 mock_collateral_breakdown 测试用，真实查询走链上 get_token_ltv()
AAVE_TOKEN_CONFIG = {
    "ETH":   {"ltv": 0.805, "liq_threshold": 0.83},
    "WBTC":  {"ltv": 0.73,  "liq_threshold": 0.78},
    "USDC":  {"ltv": 0.77,  "liq_threshold": 0.80},
    "USDT":  {"ltv": 0.75,  "liq_threshold": 0.78},
    "DAI":   {"ltv": 0.77,  "liq_threshold": 0.80},
    "LINK":  {"ltv": 0.53,  "liq_threshold": 0.68},
    "AAVE":  {"ltv": 0.60,  "liq_threshold": 0.70},
    "WSTETH": {"ltv": 0.69,  "liq_threshold": 0.81},
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 查询函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_position(wallet_address: str, rpc_url: str | None = None) -> dict:
    """查询一个地址在 Aave V3 上的仓位"""
    w3, pool, _, _ = _get_contracts(rpc_url)
    wallet_address = w3.to_checksum_address(wallet_address)
    data = pool.functions.getUserAccountData(wallet_address).call()

    health         = data[5] / 1e18
    collateral_usd = data[0] / 1e8
    debt_usd       = data[1] / 1e8

    return {
        "wallet":        wallet_address,
        "collateral":    collateral_usd,
        "debt":          debt_usd,
        "health":        health,
        "liq_threshold": data[3] / 10000,  # basis points → 百分比
        "ltv":           data[4] / 10000,
    }


def get_token_price(symbol: str, rpc_url: str | None = None) -> dict:
    """从 Chainlink 链上预言机读取代币实时 USD 价格。
    WSTETH 特殊处理：wstETH/USD = getStETHByWstETH(1e18)/1e18 × stETH/USD
    """
    w3, _, _, wsteth_contract = _get_contracts(rpc_url)
    symbol = symbol.upper()

    if symbol == "WSTETH":
        # 1. 查 1 wstETH 能换多少 stETH（汇率，18位小数）
        steth_per_wsteth = wsteth_contract.functions.getStETHByWstETH(10**18).call() / 1e18
        # 2. 查 stETH/USD 价格
        steth_feed = w3.eth.contract(
            address=w3.to_checksum_address(STETH_USD_FEED),
            abi=CHAINLINK_ABI,
        )
        _, answer, _, updated_at, _ = steth_feed.functions.latestRoundData().call()
        steth_usd = answer / 1e8
        # 3. wstETH/USD = 汇率 × stETH/USD
        price_usd = round(steth_per_wsteth * steth_usd, 4)
        return {
            "symbol":            "WSTETH",
            "price_usd":         price_usd,
            "steth_per_wsteth":  round(steth_per_wsteth, 6),
            "steth_usd":         round(steth_usd, 4),
            "source":            "wstETH contract × Chainlink stETH/USD",
            "updated_at":        updated_at,
        }

    if symbol not in CHAINLINK_FEEDS:
        return {"error": f"不支持的代币：{symbol}，支持：{list(CHAINLINK_FEEDS.keys()) + ['WSTETH']}"}

    feed = w3.eth.contract(
        address=w3.to_checksum_address(CHAINLINK_FEEDS[symbol]),
        abi=CHAINLINK_ABI,
    )
    _, answer, _, updated_at, _ = feed.functions.latestRoundData().call()

    return {
        "symbol":     symbol,
        "price_usd":  round(answer / 1e8, 4),
        "source":     "Chainlink On-chain Oracle",
        "updated_at": updated_at,
    }


def get_token_ltv(symbol: str, rpc_url: str | None = None) -> dict:
    """
    从链上 AaveProtocolDataProvider 查询代币的 LTV 和清算阈值（实时数据）

    - LTV（cfg[1]）：存入该代币最多能借多少，决定初始借款上限
    - 清算阈值（cfg[2]）：跌到这个比例触发清算，用于计算健康度
    两者不同：清算阈值 > LTV，中间的差值是 Aave 留的缓冲区
    """
    w3, _, data_provider, _ = _get_contracts(rpc_url)
    symbol = symbol.upper()
    address = TOKEN_SYMBOL_TO_ADDRESS.get(symbol)
    if not address:
        return {"error": f"不支持的代币：{symbol}，支持：{list(TOKEN_SYMBOL_TO_ADDRESS.keys())}"}

    cfg = data_provider.functions.getReserveConfigurationData(
        w3.to_checksum_address(address)
    ).call()

    ltv           = cfg[1] / 10000   # basis points → 小数，例如 8050 → 0.805
    liq_threshold = cfg[2] / 10000   # 例如 8300 → 0.83

    return {
        "symbol":            symbol,
        "ltv":               ltv,            # 借款上限（进场时用）
        "liq_threshold":     liq_threshold,  # 清算红线（健康度计算用）
        "ltv_pct":           f"{ltv:.1%}",
        "liq_threshold_pct": f"{liq_threshold:.1%}",
        "meaning": (
            f"存入 {symbol} 最多可借其价值的 {ltv:.1%}（LTV），"
            f"但抵押率跌破 {liq_threshold:.1%}（清算阈值）才触发清算，"
            f"中间 {liq_threshold - ltv:.1%} 是缓冲区"
        ),
    }


def get_user_collateral_breakdown(wallet_address: str, rpc_url: str | None = None) -> dict:
    """
    查询用户每种代币的质押和借款明细（同一个循环，减少 RPC 调用次数）：
    - collateral_tokens：各质押代币数量、USD 价值、LTV、清算阈值
    - borrow_tokens：各借款代币数量和 USD 价值
    - 加权平均清算阈值（与 getUserAccountData 返回值一致）
    """
    w3, _, data_provider, _ = _get_contracts(rpc_url)
    wallet_address = w3.to_checksum_address(wallet_address)
    reserves = [w3.to_checksum_address(addr) for addr in TOKEN_ADDRESS_TO_SYMBOL.keys()]

    collateral_tokens    = []
    borrow_tokens        = []
    total_collateral_usd = 0.0
    total_debt_usd       = 0.0

    for reserve in reserves:
        user_data          = data_provider.functions.getUserReserveData(reserve, wallet_address).call()
        a_token_balance    = user_data[0]   # 质押余额
        stable_debt        = user_data[1]   # 稳定利率借款
        variable_debt      = user_data[2]   # 浮动利率借款
        collateral_enabled = user_data[8]   # 是否启用为抵押

        has_collateral = a_token_balance > 0 and collateral_enabled
        has_borrow     = stable_debt + variable_debt > 0

        if not has_collateral and not has_borrow:
            continue

        cfg           = data_provider.functions.getReserveConfigurationData(reserve).call()
        decimals      = cfg[0]
        ltv           = cfg[1] / 10000
        liq_threshold = cfg[2] / 10000

        symbol = TOKEN_ADDRESS_TO_SYMBOL.get(
            w3.to_checksum_address(reserve), reserve[:10] + "..."
        )

        # 查实时价格（统一走 get_token_price，兼容 WSTETH 特殊计算）
        price_data = get_token_price(symbol, rpc_url)
        price_usd  = price_data.get("price_usd") if "error" not in price_data else None

        if has_collateral:
            amount    = a_token_balance / (10 ** decimals)
            value_usd = round(amount * price_usd, 2) if price_usd else None
            if value_usd:
                total_collateral_usd += value_usd
            collateral_tokens.append({
                "symbol":            symbol,
                "amount":            round(amount, 6),
                "price_usd":         price_usd,
                "value_usd":         value_usd,
                "ltv":               ltv,
                "liq_threshold":     liq_threshold,
                "ltv_pct":           f"{ltv:.0%}",
                "liq_threshold_pct": f"{liq_threshold:.0%}",
            })

        if has_borrow:
            borrow_amount = (stable_debt + variable_debt) / (10 ** decimals)
            value_usd     = round(borrow_amount * price_usd, 2) if price_usd else None
            if value_usd:
                total_debt_usd += value_usd
            borrow_tokens.append({
                "symbol":    symbol,
                "amount":    round(borrow_amount, 6),
                "price_usd": price_usd,
                "value_usd": value_usd,
            })

    # 加权平均清算阈值
    if total_collateral_usd > 0:
        weighted_liq = sum(
            t["value_usd"] * t["liq_threshold"]
            for t in collateral_tokens if t["value_usd"]
        ) / total_collateral_usd
    else:
        weighted_liq = 0.0

    return {
        "wallet":                 wallet_address,
        "collateral_tokens":      collateral_tokens,
        "total_collateral_usd":   round(total_collateral_usd, 2),
        "weighted_liq_threshold": round(weighted_liq, 4),
        "weighted_liq_pct":       f"{weighted_liq:.2%}",
        "borrow_tokens":          borrow_tokens,
        "total_debt_usd":         round(total_debt_usd, 2),
    }


def mock_position(wallet: str, collateral: float, debt: float,
                  liq_threshold: float = 0.80) -> dict:
    """模拟一个仓位（用于开发测试）"""
    health = (collateral * liq_threshold / debt) if debt > 0 else float("inf")
    return {
        "wallet":        wallet,
        "collateral":    collateral,
        "debt":          debt,
        "health":        health,
        "liq_threshold": liq_threshold,
        "ltv":           liq_threshold - 0.05,
    }


def mock_collateral_breakdown(wallet: str, tokens: list, borrows: list = None) -> dict:
    """
    模拟混合质押和借款明细（用于开发测试，格式与 get_user_collateral_breakdown 相同）

    tokens 示例：
    [{"symbol": "ETH", "amount": 2.0, "price_usd": 2000.0}, ...]

    borrows 示例（可选）：
    [{"symbol": "USDC", "amount": 3000, "price_usd": 1.0}, ...]
    """
    result_tokens = []
    total_collateral_usd = 0.0

    for t in tokens:
        cfg = AAVE_TOKEN_CONFIG.get(t["symbol"], {"ltv": 0.75, "liq_threshold": 0.80})
        value_usd = round(t["amount"] * t["price_usd"], 2)
        total_collateral_usd += value_usd
        result_tokens.append({
            "symbol":            t["symbol"],
            "amount":            t["amount"],
            "price_usd":         t["price_usd"],
            "value_usd":         value_usd,
            "ltv":               cfg["ltv"],
            "liq_threshold":     cfg["liq_threshold"],
            "ltv_pct":           f"{cfg['ltv']:.0%}",
            "liq_threshold_pct": f"{cfg['liq_threshold']:.0%}",
        })

    weighted_liq = (
        sum(t["value_usd"] * t["liq_threshold"] for t in result_tokens)
        / total_collateral_usd
        if total_collateral_usd > 0 else 0.0
    )

    result_borrows = []
    total_debt_usd = 0.0
    for b in (borrows or []):
        value_usd = round(b["amount"] * b["price_usd"], 2)
        total_debt_usd += value_usd
        result_borrows.append({
            "symbol":    b["symbol"],
            "amount":    b["amount"],
            "price_usd": b["price_usd"],
            "value_usd": value_usd,
        })

    return {
        "wallet":                 wallet,
        "collateral_tokens":      result_tokens,
        "total_collateral_usd":   round(total_collateral_usd, 2),
        "weighted_liq_threshold": round(weighted_liq, 4),
        "weighted_liq_pct":       f"{weighted_liq:.2%}",
        "borrow_tokens":          result_borrows,
        "total_debt_usd":         round(total_debt_usd, 2),
    }


def print_price(price_data: dict):
    """格式化打印 Chainlink 价格"""
    if "error" in price_data:
        print(f"  ❌ {price_data['error']}")
        return
    print(f"  {price_data['symbol']:6s}  ${price_data['price_usd']:>12,.4f} USD  (Chainlink 链上报价)")


def print_position(pos: dict, breakdown: dict = None):
    """格式化打印仓位信息"""
    if pos["health"] > 1e10:
        print(f"\n地址 {pos['wallet']}")
        print(f"  抵押: ${pos['collateral']:,.2f}，但没有借款，健康度无穷大")
        return

    if pos["health"] == 0 and pos["debt"] == 0:
        print(f"\n地址 {pos['wallet']}")
        print("  → 该地址在 Aave V3 上没有借款仓位")
        return

    if breakdown:
        alert_t, danger_t = compute_weighted_thresholds(breakdown)
    else:
        alert_t, danger_t = _DEFAULT_THRESHOLDS["alert"], _DEFAULT_THRESHOLDS["danger"]

    if pos["health"] >= alert_t:
        risk = "🟢 安全"
    elif pos["health"] >= danger_t:
        risk = "🟡 注意"
    else:
        risk = "🔴 危险（即将清算）"

    print(f"\n{'='*55}")
    print(f"  地址:     {pos['wallet']}")
    print(f"  总抵押:   ${pos['collateral']:,.2f}")
    print(f"  总借款:   ${pos['debt']:,.2f}")
    print(f"  健康度:   {pos['health']:.4f}  {risk}")
    print(f"  清算阈值: {pos['liq_threshold']:.1%}（加权）")
    print(f"  当前 LTV: {pos['ltv']:.1%}（加权）")

    if breakdown and breakdown.get("collateral_tokens"):
        print(f"  {'─'*51}")
        print(f"  质押明细")
        print(f"  {'代币':<7} {'数量':>13} {'单价':>13} {'价值(USD)':>12} {'清算阈值':>6}")
        print(f"  {'─'*51}")
        for t in breakdown["collateral_tokens"]:
            print(
                f"  {t['symbol']:<7}"
                f" {t['amount']:>13,.4f}"
                f" ${t['price_usd']:>11,.2f}"
                f" ${t['value_usd']:>11,.2f}"
                f" {t['liq_threshold_pct']:>6}"
            )
        print(f"  {'─'*51}")
        print(f"  {'总计':<7} {'':>13} {'':>13} ${breakdown['total_collateral_usd']:>11,.2f}")
        print(f"  加权清算阈值: {breakdown['weighted_liq_pct']}")

    if breakdown and breakdown.get("borrow_tokens"):
        print(f"  {'─'*51}")
        print(f"  借款明细")
        print(f"  {'代币':<7} {'数量':>13} {'单价':>13} {'价值(USD)':>12}")
        print(f"  {'─'*51}")
        for b in breakdown["borrow_tokens"]:
            print(
                f"  {b['symbol']:<7}"
                f" {b['amount']:>13,.4f}"
                f" ${b['price_usd']:>11,.2f}"
                f" ${b['value_usd']:>11,.2f}"
            )
        print(f"  {'─'*51}")
        print(f"  {'总计':<7} {'':>13} {'':>13} ${breakdown['total_debt_usd']:>11,.2f}")

    print(f"{'='*55}")


if __name__ == "__main__":
    print("=" * 55)
    print("  模式 1：模拟仓位（单一质押 ETH，三档风险）")
    print("=" * 55)
    ETH_MOCK_PRICE = 2000.0
    for label, collateral, debt in [
        ("0xUser_Safe",    10000, 3000),
        ("0xUser_Warning", 10000, 6500),
        ("0xUser_Danger",  10000, 8500),
    ]:
        bd  = mock_collateral_breakdown(
            label,
            tokens=[{"symbol": "ETH", "amount": collateral / ETH_MOCK_PRICE, "price_usd": ETH_MOCK_PRICE}],
            borrows=[{"symbol": "USDC", "amount": debt, "price_usd": 1.0}],
        )
        pos = mock_position(label, collateral=collateral, debt=debt,
                            liq_threshold=bd["weighted_liq_threshold"])
        print_position(pos, bd)

    print("\n")
    print("=" * 55)
    print("  模式 2：Chainlink 链上实时价格")
    print("=" * 55)
    for symbol in ["ETH", "WBTC", "USDC"]:
        print_price(get_token_price(symbol))

    print("\n")
    print("=" * 55)
    print("  模式 3：模拟混合质押（ETH + WBTC + USDC）")
    print("=" * 55)
    bd_mock = mock_collateral_breakdown(
        wallet="0xMixed_User",
        tokens=[
            {"symbol": "ETH",  "amount": 2.0,  "price_usd": 2000.0},
            {"symbol": "WBTC", "amount": 0.05, "price_usd": 60000.0},
            {"symbol": "USDC", "amount": 3000, "price_usd": 1.0},
        ],
        borrows=[
            {"symbol": "USDT", "amount": 5000, "price_usd": 1.0},
            {"symbol": "DAI",  "amount": 2500, "price_usd": 1.0},
        ],
    )
    pos_mock = mock_position(
        wallet="0xMixed_User",
        collateral=bd_mock["total_collateral_usd"],
        debt=7500,
        liq_threshold=bd_mock["weighted_liq_threshold"],
    )
    print_position(pos_mock, bd_mock)

    print("\n")
    print("=" * 55)
    print("  模式 4：查询真实链上地址")
    print("=" * 55)
    my_wallet = os.getenv("WALLET_ADDRESS")
    if my_wallet and my_wallet.startswith("0x"):
        pos = get_position(my_wallet)
        if pos["debt"] > 0 and pos["health"] < 1e10:
            breakdown = get_user_collateral_breakdown(my_wallet)
            print_position(pos, breakdown)
        else:
            print_position(pos)
    else:
        print("\n  提示：在 .env 里填入 WALLET_ADDRESS 即可查询你自己的仓位")
