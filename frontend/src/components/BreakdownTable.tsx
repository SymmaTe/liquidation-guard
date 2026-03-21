'use client'

import { useFullBreakdown, type TokenDetail } from '@/hooks/usePosition'

function Table({
  title,
  rows,
  emptyText,
}: {
  title: string
  rows: TokenDetail[]
  emptyText: string
}) {
  return (
    <div className="bg-white/5 border border-white/8 rounded-2xl p-6">
      <h2 className="text-base font-medium text-gray-300 mb-5">{title}</h2>
      {rows.length === 0 ? (
        <p className="text-base text-gray-600 text-center py-6">{emptyText}</p>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="text-sm text-gray-500 border-b border-white/8">
              <th className="text-left pb-3 font-medium">代币</th>
              <th className="text-right pb-3 font-medium">数量</th>
              <th className="text-right pb-3 font-medium">价值 (USD)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.symbol} className="border-b border-white/5 last:border-0">
                <td className="py-3.5 text-base font-semibold text-white">{row.symbol}</td>
                <td className="py-3.5 text-right text-base font-mono text-gray-400">
                  {row.amount.toLocaleString('en', { maximumFractionDigits: 4 })}
                </td>
                <td className="py-3.5 text-right text-base font-mono text-gray-200">
                  ${row.valueUsd.toLocaleString('en', { maximumFractionDigits: 0 })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export function BreakdownTable({ address }: { address: `0x${string}` }) {
  const { collateral, borrows, isLoading } = useFullBreakdown(address)

  if (isLoading) return (
    <div className="grid grid-cols-2 gap-4">
      {[0, 1].map(i => (
        <div key={i} className="bg-white/5 border border-white/8 rounded-2xl p-6 animate-pulse">
          <div className="h-5 bg-white/10 rounded w-24 mb-5" />
          <div className="space-y-3">
            {[0,1,2].map(j => <div key={j} className="h-10 bg-white/10 rounded" />)}
          </div>
        </div>
      ))}
    </div>
  )

  return (
    <div className="grid grid-cols-2 gap-4">
      <Table title="质押明细" rows={collateral} emptyText="未质押任何资产" />
      <Table title="借款明细" rows={borrows}    emptyText="未借出任何资产" />
    </div>
  )
}
