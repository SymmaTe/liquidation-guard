'use client'

import { useState, useEffect } from 'react'
import { usePosition, useFullBreakdown } from '@/hooks/usePosition'
import { loadSettings, computeWeightedThresholds } from '@/lib/settings'

function riskLabel(health: number, warningHF: number, dangerHF: number) {
  if (health >= warningHF) return { text: '安全', color: 'text-green-400', bg: 'bg-green-400/10 border-green-400/20' }
  if (health >= dangerHF)  return { text: '注意', color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/20' }
  return { text: '紧急', color: 'text-red-400', bg: 'bg-red-400/10 border-red-400/20' }
}

function StatBox({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white/5 border border-white/8 rounded-2xl p-6">
      <p className="text-sm text-gray-400 mb-2">{label}</p>
      <p className="text-2xl font-mono font-bold text-white break-all">{value}</p>
      {sub && <p className="text-sm text-gray-500 mt-2">{sub}</p>}
    </div>
  )
}

export function PositionCard({ address }: { address: `0x${string}` }) {
  const { position, isLoading, error } = usePosition(address)
  const { collateral: collateralTokens } = useFullBreakdown(address)
  const [warningHF, setWarningHF] = useState(1.4)
  const [dangerHF, setDangerHF] = useState(1.1)

  useEffect(() => {
    const s = loadSettings()
    if (s.customThresholds.enabled) {
      setWarningHF(s.customThresholds.warningHF)
      setDangerHF(s.customThresholds.dangerHF)
    } else {
      const { warningHF, dangerHF } = computeWeightedThresholds(collateralTokens)
      setWarningHF(warningHF)
      setDangerHF(dangerHF)
    }
  }, [collateralTokens])

  if (isLoading) return (
    <div className="bg-white/5 border border-white/8 rounded-2xl p-8 animate-pulse">
      <div className="h-6 bg-white/10 rounded w-32 mb-6" />
      <div className="grid grid-cols-3 gap-4">
        {[0,1,2].map(i => <div key={i} className="h-28 bg-white/10 rounded-2xl" />)}
      </div>
    </div>
  )

  if (error) return (
    <div className="bg-white/5 border border-red-500/20 rounded-2xl p-8 text-red-400">
      读取仓位失败：{error.message}
    </div>
  )

  if (!position) return null

  const { collateral, debt, health, noDebt } = position
  const risk = noDebt
    ? { text: '无借款', color: 'text-blue-400', bg: 'bg-blue-400/10 border-blue-400/20' }
    : riskLabel(health, warningHF, dangerHF)

  return (
    <div className="bg-white/5 border border-white/8 rounded-2xl p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-base font-medium text-gray-400">仓位总览</h2>
        <span className={`text-sm font-bold px-3 py-1 rounded-full border ${risk.bg} ${risk.color}`}>
          {risk.text}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatBox
          label="总抵押"
          value={`$${collateral.toLocaleString('en', { maximumFractionDigits: 2 })}`}
        />
        <StatBox
          label="总借款"
          value={noDebt ? '$0' : `$${debt.toLocaleString('en', { maximumFractionDigits: 2 })}`}
        />
        <StatBox
          label="健康因子"
          value={noDebt ? '∞' : health.toFixed(4)}
          sub={noDebt ? undefined : `清算阈值 ${(position.liqThreshold * 100).toFixed(1)}%`}
        />
      </div>
    </div>
  )
}
