'use client'

// 'use client' 告诉 Next.js 这个文件在浏览器里运行（而不是服务器）
// 钱包连接必须在浏览器里，所以需要这个声明

import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { config } from '@/lib/wagmi'

// QueryClient 负责缓存链上读取结果，避免重复请求
const queryClient = new QueryClient()

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </WagmiProvider>
  )
}
