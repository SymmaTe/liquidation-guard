import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'
import { Sidebar } from '@/components/Sidebar'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Liquidation Guard',
  description: 'Aave V3 仓位监控与清算保护',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
      <body className="min-h-screen bg-grid text-gray-100 antialiased">
        <Providers>
          <Sidebar />
          {/* 主内容区，左边留出侧边栏宽度 */}
          <main className="ml-56 min-h-screen">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  )
}
