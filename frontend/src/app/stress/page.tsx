'use client'

import { useState, useEffect } from 'react'
import { isAddress } from 'viem'
import { useConnection } from 'wagmi'
import { ClientOnly } from '@/components/ClientOnly'
import { usePosition } from '@/hooks/usePosition'
import { useFullBreakdown, type TokenDetail } from '@/hooks/usePosition'
import { type TokenSymbol } from '@/lib/aave'

function riskColor(health: number) {
  if (health >= 1.5) return 'text-green-400'
  if (health >= 1.1) return 'text-yellow-400'
  return 'text-red-400'
}

function TokenSlider({
  token,
  value,
  onChange,
  mode,
}: {
  token: TokenDetail
  value: number
  onChange: (v: number) => void
  mode: 'drop' | 'rise'
}) {
  const isStable = token.isStable
  const locked = isStable
  const label = mode === 'drop' ? `下跌 ${value}%` : `上涨 ${value}%`
  const newValue = mode === 'drop'
    ? token.valueUsd * (1 - value / 100)
    : token.valueUsd * (1 + value / 100)

  return (
    <div className={`rounded-xl p-5 border transition-colors ${locked ? 'border-white/5 opacity-40' : 'border-white/8 bg-white/3'}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold text-white">{token.symbol}</span>
          {isStable && (
            <span className="text-xs text-blue-400 bg-blue-400/10 px-1.5 py-0.5 rounded">稳定币</span>
          )}
        </div>
        <span className={`text-base font-mono font-bold ${locked ? 'text-gray-600' : mode === 'drop' ? 'text-red-400' : 'text-green-400'}`}>
          {locked ? '锁定 0%' : label}
        </span>
      </div>

      {/* 用 div 覆盖来阻止稳定币交互 */}
      <div className="relative">
        <input
          type="range"
          min={0}
          max={90}
          value={locked ? 0 : value}
          onChange={e => !locked && onChange(Number(e.target.value))}
          className="w-full h-2 accent-blue-500 cursor-pointer mb-3"
        />
        {locked && <div className="absolute inset-0 cursor-not-allowed" />}
      </div>

      <div className="flex justify-between text-xs text-gray-500">
        <span>${token.valueUsd.toLocaleString('en', { maximumFractionDigits: 0 })} 当前</span>
        <span className={mode === 'drop' ? 'text-red-400' : 'text-green-400'}>
          ${newValue.toLocaleString('en', { maximumFractionDigits: 0 })} 模拟后
        </span>
      </div>
    </div>
  )
}

function HealthBar({ current, simulated }: { current: number; simulated: number }) {
  const toPercent = (hf: number) => Math.min(Math.max((hf - 1) / 1.0 * 100, 0), 100)
  const simPct = toPercent(simulated)
  const curPct = toPercent(current)

  // 模拟后颜色：绿 / 黄 / 红
  const simFill = simulated >= 1.5 ? 'bg-green-500' : simulated >= 1.1 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-2">
        <span>清算线 HF=1.0</span>
        <span>安全 HF≥1.5</span>
      </div>
      <div className="relative h-4 bg-white/8 rounded-full border border-white/10">
        {/* 模拟后填充 */}
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-300 ${simFill}`}
          style={{ width: `${simPct}%` }}
        />
        {/* 当前 HF 白色竖线标记 */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_6px_white] transition-all duration-300"
          style={{ left: `${curPct}%` }}
        />
        {/* 安全线虚线 */}
        <div className="absolute inset-y-0 left-[50%] w-px bg-green-400/30" />
      </div>
      <div className="flex justify-between text-xs mt-2">
        <span className="text-gray-400">当前 <span className="text-white font-mono">{current.toFixed(4)}</span></span>
        <span className={riskColor(simulated)}>模拟 <span className="font-mono">{simulated <= 0 ? '已清算' : simulated.toFixed(4)}</span></span>
      </div>
    </div>
  )
}

function Simulator({ address }: { address: `0x${string}` }) {
  const { position } = usePosition(address)
  const { collateral, borrows, isLoading } = useFullBreakdown(address)

  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  // 每个代币的滑块值
  const [collateralDrops, setCollateralDrops] = useState<Record<TokenSymbol, number>>({} as Record<TokenSymbol, number>)
  const [borrowRises, setBorrowRises] = useState<Record<TokenSymbol, number>>({} as Record<TokenSymbol, number>)

  if (!mounted || isLoading) return (
    <div className="space-y-4">
      {[0,1,2].map(i => (
        <div key={i} className="bg-white/5 border border-white/8 rounded-2xl p-6 animate-pulse h-32" />
      ))}
    </div>
  )

  if (!position || position.noDebt) return (
    <div className="bg-white/5 border border-white/8 rounded-2xl p-8 text-center text-gray-500">
      该地址没有借款，无需模拟清算风险。
    </div>
  )

  // 计算模拟后的抵押价值和加权清算阈值
  let newCollateralTotal = 0
  let newWeightedLiq = 0
  for (const token of collateral) {
    const drop = token.isStable ? 0 : (collateralDrops[token.symbol] ?? 0)
    const newVal = token.valueUsd * (1 - drop / 100)
    newCollateralTotal += newVal
    newWeightedLiq += newVal * token.liqThreshold
  }
  const newWeightedLiqRatio = newCollateralTotal > 0 ? newWeightedLiq / newCollateralTotal : 0

  // 计算模拟后的借款价值
  let newDebtTotal = 0
  for (const token of borrows) {
    const rise = borrowRises[token.symbol] ?? 0
    newDebtTotal += token.valueUsd * (1 + rise / 100)
  }

  const newHealth = newDebtTotal > 0
    ? (newCollateralTotal * newWeightedLiqRatio) / newDebtTotal
    : Infinity

  // 触发清算需要的额外下跌（仅抵押侧，借款不变时）
  const criticalDrop = position.liqThreshold > 0
    ? (1 - position.debt / (position.collateral * position.liqThreshold)) * 100
    : 100

  return (
    <div className="flex flex-col gap-5">

      {/* 结果摘要 */}
      <div className="bg-white/5 border border-white/8 rounded-2xl p-6">
        <h2 className="text-base font-medium text-gray-400 mb-5">模拟结果</h2>
        <HealthBar current={position.health} simulated={newHealth} />

        <div className="grid grid-cols-2 gap-4 mt-5">
          <div className="bg-white/5 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">模拟后健康因子</p>
            <p className={`text-2xl font-mono font-bold ${riskColor(newHealth)}`}>
              {newHealth <= 0 ? '已清算' : newHealth === Infinity ? '∞' : newHealth.toFixed(4)}
            </p>
          </div>
          <div className="bg-white/5 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">抵押品整体再跌多少触发清算</p>
            <p className="text-2xl font-mono font-bold text-white">
              -{criticalDrop.toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* 抵押品滑块 */}
      {collateral.length > 0 && (
        <div className="bg-white/5 border border-white/8 rounded-2xl p-6">
          <h2 className="text-base font-medium text-gray-400 mb-4">质押代币价格下跌</h2>
          <div className="space-y-3">
            {collateral.map(token => (
              <TokenSlider
                key={token.symbol}
                token={token}
                value={collateralDrops[token.symbol] ?? 0}
                onChange={v => setCollateralDrops(prev => ({ ...prev, [token.symbol]: v }))}
                mode="drop"
              />
            ))}
          </div>
        </div>
      )}

      {/* 借款滑块 */}
      {borrows.length > 0 && (
        <div className="bg-white/5 border border-white/8 rounded-2xl p-6">
          <h2 className="text-base font-medium text-gray-400 mb-4">借出代币价格上涨</h2>
          <div className="space-y-3">
            {borrows.map(token => (
              <TokenSlider
                key={token.symbol}
                token={token}
                value={borrowRises[token.symbol] ?? 0}
                onChange={v => setBorrowRises(prev => ({ ...prev, [token.symbol]: v }))}
                mode="rise"
              />
            ))}
          </div>
        </div>
      )}

    </div>
  )
}

function StressContent({ input, setInput }: { input: string; setInput: (v: string) => void }) {
  const { address: walletAddress, isConnected } = useConnection()
  const queryAddress = (isAddress(input) ? input : walletAddress) as `0x${string}` | undefined
  const placeholder = isConnected && walletAddress ? walletAddress : '0x... 输入钱包地址'

  return (
    <>
      <div className="mb-6">
        <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-2xl px-5 py-4 focus-within:border-blue-500/50 transition-colors">
          <span className="text-gray-500 text-sm shrink-0">地址</span>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-sm font-mono text-gray-200 placeholder:text-gray-600 outline-none"
          />
          {input && <button onClick={() => setInput('')} className="text-gray-600 hover:text-gray-300 text-xs shrink-0">清除</button>}
          {input && !isAddress(input) && <span className="text-red-400 text-xs shrink-0">格式错误</span>}
        </div>
      </div>

      {queryAddress ? (
        <Simulator address={queryAddress} />
      ) : (
        <div className="flex flex-col items-center gap-5 text-center py-24">
          <div className="w-20 h-20 rounded-2xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center text-4xl">◇</div>
          <div>
            <h2 className="text-xl font-bold text-white mb-2">输入地址开始模拟</h2>
            <p className="text-gray-500 text-sm max-w-xs">每种代币独立设置涨跌幅，实时计算健康因子变化。</p>
          </div>
        </div>
      )}
    </>
  )
}

export default function StressPage() {
  const [input, setInput] = useState('')

  useEffect(() => {
    setInput(localStorage.getItem('queryAddress') ?? '')
  }, [])

  const handleSetInput = (v: string) => {
    setInput(v)
    localStorage.setItem('queryAddress', v)
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-10 py-10">
      <div className="w-full max-w-3xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">压力测试</h1>
          <p className="text-gray-500 text-base mt-2">模拟各代币价格变化对健康因子的影响</p>
        </div>
        <ClientOnly>
          <StressContent input={input} setInput={handleSetInput} />
        </ClientOnly>
      </div>
    </div>
  )
}
