'use client'

import { usePosition } from '@/hooks/usePosition'
import { useFullBreakdown } from '@/hooks/usePosition'
import { STABLE_TOKENS } from '@/lib/aave'

// 正确公式：其他代币价格不变，单代币跌至何价触发清算
// totalWeightedLiq = totalCollateral × weightedLiqThreshold
// otherWeightedLiq = totalWeightedLiq - token_value_i × token_liqThreshold_i
// liq_price_i = (debt - otherWeightedLiq) / (token_amount_i × token_liqThreshold_i)
function calcLiqPrice(
  tokenValue: number,
  tokenAmount: number,
  tokenLiqThreshold: number,
  totalCollateral: number,
  totalDebt: number,
  weightedLiqThreshold: number,
): number | null {
  if (tokenAmount <= 0 || tokenLiqThreshold <= 0) return null
  const totalWeightedLiq = totalCollateral * weightedLiqThreshold
  const otherWeightedLiq = totalWeightedLiq - tokenValue * tokenLiqThreshold
  const price = (totalDebt - otherWeightedLiq) / (tokenAmount * tokenLiqThreshold)
  return price > 0 ? price : null
}

export function LiquidationPrices({ address }: { address: `0x${string}` }) {
  const { position } = usePosition(address)
  const { collateral, isLoading } = useFullBreakdown(address)

  if (isLoading || !position || position.noDebt) return null

  const volatile = collateral.filter(t => !STABLE_TOKENS.includes(t.symbol as typeof STABLE_TOKENS[number]))
  if (volatile.length === 0) return null

  const { collateral: totalCollateral, debt, liqThreshold } = position

  return (
    <div className="bg-white/5 border border-white/8 rounded-2xl p-6">
      <h2 className="text-base font-medium text-gray-300 mb-4">清算价格估算</h2>
      <p className="text-xs text-gray-600 mb-4">假设其他代币价格不变，单一代币跌至此价格触发清算</p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {volatile.map(token => {
          const liqPrice = calcLiqPrice(
            token.valueUsd, token.amount, token.liqThreshold,
            totalCollateral, debt, liqThreshold,
          )
          if (!liqPrice) return null
          const dropPct = ((token.priceUsd - liqPrice) / token.priceUsd * 100)

          return (
            <div key={token.symbol} className="bg-white/5 rounded-xl p-4">
              <p className="text-sm font-semibold text-white mb-1">{token.symbol}</p>
              <p className="text-lg font-mono font-bold text-red-400">
                ${liqPrice.toLocaleString('en', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                现价 ${token.priceUsd.toLocaleString('en', { maximumFractionDigits: 0 })} · 再跌 {dropPct.toFixed(1)}%
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
