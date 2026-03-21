import { useReadContract, useReadContracts } from 'wagmi'
import { AAVE_POOL_ADDRESS, AAVE_DATA_PROVIDER, POOL_ABI, DATA_PROVIDER_ABI, CHAINLINK_ABI, CHAINLINK_FEEDS, TOKENS, type TokenSymbol } from '@/lib/aave'
import { formatUnits } from 'viem'

export type TokenDetail = {
  symbol: TokenSymbol
  amount: number
  priceUsd: number
  valueUsd: number
  liqThreshold: number  // 0~1，只对抵押品有意义
  isStable: boolean
}

// useReadContract = 调用合约的 view 函数（只读，不花 gas）
// 类比 Python 的 contract.functions.xxx().call()

export function usePosition(address?: `0x${string}`) {
  const { data, isLoading, error } = useReadContract({
    address: AAVE_POOL_ADDRESS,
    abi: POOL_ABI,
    functionName: 'getUserAccountData',
    args: address ? [address] : undefined,
    query: { enabled: !!address, refetchInterval: 30_000 }, // 30秒自动刷新
  })

  if (!data) return { position: null, isLoading, error }

  const [totalCollateralBase, totalDebtBase, , currentLiquidationThreshold, , healthFactor] = data

  // Aave 返回的单位是 USD × 1e8（8位小数），健康因子是 × 1e18
  const collateral = Number(formatUnits(totalCollateralBase, 8))
  const debt = Number(formatUnits(totalDebtBase, 8))
  const health = Number(formatUnits(healthFactor, 18))
  const liqThreshold = Number(currentLiquidationThreshold) / 10000

  const noDebt = debt < 0.01

  return {
    position: { collateral, debt, health, liqThreshold, noDebt },
    isLoading,
    error,
  }
}

export function useTokenBreakdown(address?: `0x${string}`) {
  const tokenList = Object.values(TOKENS)

  // 批量调用：一次 RPC 请求读取所有代币的余额
  const { data, isLoading } = useReadContracts({
    contracts: tokenList.map((token) => ({
      address: AAVE_DATA_PROVIDER,
      abi: DATA_PROVIDER_ABI,
      functionName: 'getUserReserveData' as const,
      args: [token.address as `0x${string}`, address!] as const,
    })),
    query: { enabled: !!address, refetchInterval: 30_000 },
  })

  if (!data) return { collateral: [], borrows: [], isLoading }

  const collateral: { symbol: TokenSymbol; amount: number }[] = []
  const borrows:    { symbol: TokenSymbol; amount: number }[] = []

  tokenList.forEach((token, i) => {
    const result = data[i]
    if (result.status !== 'success') return
    const [aTokenBalance, stableDebt, variableDebt] = result.result as unknown as [bigint, bigint, bigint]

    const supplied = Number(formatUnits(aTokenBalance, token.decimals))
    const borrowed = Number(formatUnits(stableDebt + variableDebt, token.decimals))

    if (supplied > 0.0001) collateral.push({ symbol: token.symbol as TokenSymbol, amount: supplied })
    if (borrowed > 0.0001) borrows.push({ symbol: token.symbol as TokenSymbol, amount: borrowed })
  })

  return { collateral, borrows, isLoading }
}

// 完整明细：含 USD 价值、清算阈值，供压力测试使用
export function useFullBreakdown(address?: `0x${string}`) {
  const tokenList = Object.entries(TOKENS) as [TokenSymbol, typeof TOKENS[TokenSymbol]][]

  // 批量：每个代币的 Aave 余额 + 清算阈值 + Chainlink 价格
  const { data, isLoading } = useReadContracts({
    contracts: tokenList.flatMap(([symbol, token]) => [
      {
        address: AAVE_DATA_PROVIDER,
        abi: DATA_PROVIDER_ABI,
        functionName: 'getUserReserveData' as const,
        args: [token.address as `0x${string}`, address!] as const,
      },
      {
        address: AAVE_DATA_PROVIDER,
        abi: DATA_PROVIDER_ABI,
        functionName: 'getReserveConfigurationData' as const,
        args: [token.address as `0x${string}`] as const,
      },
      {
        address: CHAINLINK_FEEDS[symbol],
        abi: CHAINLINK_ABI,
        functionName: 'latestRoundData' as const,
        args: [] as const,
      },
    ]),
    query: { enabled: !!address, refetchInterval: 30_000 },
  })

  if (!data) return { collateral: [] as TokenDetail[], borrows: [] as TokenDetail[], isLoading }

  const collateral: TokenDetail[] = []
  const borrows: TokenDetail[] = []
  const STABLE_TOKENS = ['USDC', 'USDT', 'DAI']

  tokenList.forEach(([symbol, token], i) => {
    const reserveResult = data[i * 3]
    const configResult  = data[i * 3 + 1]
    const priceResult   = data[i * 3 + 2]

    if (reserveResult.status !== 'success') return
    if (configResult.status  !== 'success') return
    if (priceResult.status   !== 'success') return

    const [aTokenBalance, stableDebt, variableDebt] = reserveResult.result as unknown as [bigint, bigint, bigint]
    const configData = configResult.result as unknown as [bigint, bigint, bigint, ...unknown[]]
    const priceData  = priceResult.result as unknown as [bigint, bigint, bigint, bigint, bigint]

    const liqThreshold = Number(configData[2]) / 10000
    const priceUsd = Number(priceData[1]) / 1e8
    const isStable = STABLE_TOKENS.includes(symbol)

    const supplied = Number(formatUnits(aTokenBalance, token.decimals))
    const borrowed = Number(formatUnits(stableDebt + variableDebt, token.decimals))

    if (supplied > 0.0001) {
      collateral.push({
        symbol, amount: supplied,
        priceUsd, valueUsd: supplied * priceUsd,
        liqThreshold, isStable,
      })
    }
    if (borrowed > 0.0001) {
      borrows.push({
        symbol, amount: borrowed,
        priceUsd, valueUsd: borrowed * priceUsd,
        liqThreshold: 0, isStable,
      })
    }
  })

  return { collateral, borrows, isLoading }
}
