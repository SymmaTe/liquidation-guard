'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useConnection, useConnect, useDisconnect } from 'wagmi'
import { injected } from 'wagmi/connectors'
import { ClientOnly } from '@/components/ClientOnly'

const NAV_ITEMS = [
  { href: '/',         icon: '◈', label: '仓位' },
  { href: '/chat',     icon: '◉', label: '对话' },
  { href: '/stress',   icon: '◇', label: '模拟' },
  { href: '/settings', icon: '◎', label: '监控设置' },
]

function shortAddress(addr: string) {
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

function WalletSection() {
  const { address, isConnected } = useConnection()
  const { mutate: connect } = useConnect()
  const { mutate: disconnect } = useDisconnect()

  if (isConnected && address) return (
    <div className="space-y-2">
      <div className="px-3 py-2.5 rounded-lg bg-white/5 border border-white/8">
        <p className="text-xs text-gray-500 mb-1">已连接</p>
        <p className="text-sm font-mono text-gray-200">{shortAddress(address)}</p>
      </div>
      <button
        onClick={() => disconnect()}
        className="w-full text-xs text-gray-600 hover:text-red-400 py-1.5 transition-colors"
      >
        断开连接
      </button>
    </div>
  )

  return (
    <button
      onClick={() => connect({ connector: injected() })}
      className="w-full bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
    >
      连接钱包
    </button>
  )
}

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 flex flex-col border-r border-white/5 bg-black/30 backdrop-blur-xl z-10">

      {/* Logo */}
      <div className="px-5 py-7 border-b border-white/5">
        <div className="flex items-center gap-3">
          <span className="text-blue-400 text-3xl">⚡</span>
          <div>
            <p className="text-xl font-bold text-white leading-tight">Liquidation</p>
            <p className="text-xl font-bold text-blue-400 leading-tight">Guard</p>
          </div>
        </div>
        <p className="text-xs text-gray-600 mt-3">Aave V3 · 以太坊主网</p>
      </div>

      {/* 导航 */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ href, icon, label }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                active
                  ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                  : 'text-gray-500 hover:text-gray-200 hover:bg-white/5'
              }`}
            >
              <span className="text-base">{icon}</span>
              <span className="font-medium">{label}</span>
            </Link>
          )
        })}
      </nav>

      {/* 钱包区域 — ClientOnly 永久解决 hydration */}
      <div className="px-3 py-4 border-t border-white/5">
        <ClientOnly>
          <WalletSection />
        </ClientOnly>
      </div>
    </aside>
  )
}
