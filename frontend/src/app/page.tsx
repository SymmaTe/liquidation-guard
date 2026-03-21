'use client'

import { useState, useEffect } from 'react'
import { isAddress } from 'viem'
import { useConnection } from 'wagmi'
import { ClientOnly } from '@/components/ClientOnly'
import { PositionCard } from '@/components/PositionCard'
import { BreakdownTable } from '@/components/BreakdownTable'
import { LiquidationPrices } from '@/components/LiquidationPrices'
import { HealthHistoryChart } from '@/components/HealthHistoryChart'

function AddressInput({
  input,
  setInput,
}: {
  input: string
  setInput: (v: string) => void
}) {
  const { address: walletAddress, isConnected } = useConnection()
  const placeholder = isConnected && walletAddress ? walletAddress : '0x... 输入任意钱包地址'

  return (
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
        {input && (
          <button onClick={() => setInput('')} className="text-gray-600 hover:text-gray-300 text-xs shrink-0">
            清除
          </button>
        )}
        {input && !isAddress(input) && (
          <span className="text-red-400 text-xs shrink-0">格式错误</span>
        )}
      </div>
      {isConnected && walletAddress && !input && (
        <p className="text-xs text-gray-600 mt-2 px-1">当前使用已连接钱包地址</p>
      )}
    </div>
  )
}

function PositionContent({ input }: { input: string }) {
  const { address: walletAddress } = useConnection()
  const queryAddress = (isAddress(input) ? input : walletAddress) as `0x${string}` | undefined

  if (!queryAddress) return (
    <div className="flex flex-col items-center gap-5 text-center py-24">
      <div className="w-20 h-20 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-4xl">⚡</div>
      <div>
        <h2 className="text-xl font-bold text-white mb-2">输入地址或连接钱包</h2>
        <p className="text-gray-500 text-sm max-w-xs">支持查看任意钱包的 Aave V3 仓位，连接自己的钱包后自动填入。</p>
      </div>
    </div>
  )

  return (
    <div className="flex flex-col gap-6">
      <PositionCard address={queryAddress} />
      <BreakdownTable address={queryAddress} />
      <LiquidationPrices address={queryAddress} />
      <HealthHistoryChart address={queryAddress} />
    </div>
  )
}

export default function Home() {
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
          <h1 className="text-3xl font-bold text-white">仓位总览</h1>
          <p className="text-gray-500 text-base mt-2">实时监控 Aave V3 抵押仓位</p>
        </div>

        {/* ClientOnly 包裹所有依赖钱包状态的内容，永久解决 hydration 问题 */}
        <ClientOnly>
          <AddressInput input={input} setInput={handleSetInput} />
          <PositionContent input={input} />
        </ClientOnly>
      </div>
    </div>
  )
}
