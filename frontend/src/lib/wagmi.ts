import { createConfig, http } from 'wagmi'
import { mainnet } from 'wagmi/chains'
import { injected } from 'wagmi/connectors'

function getRpcUrl(): string | undefined {
  if (typeof window === 'undefined') return process.env.NEXT_PUBLIC_RPC_URL
  try {
    const raw = localStorage.getItem('appSettings')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed?.rpcUrl) return parsed.rpcUrl
    }
  } catch {}
  return process.env.NEXT_PUBLIC_RPC_URL ?? 'https://eth.llamarpc.com'
}

export const config = createConfig({
  chains: [mainnet],
  connectors: [
    injected(), // MetaMask 等浏览器插件钱包
  ],
  transports: {
    [mainnet.id]: http(getRpcUrl()),
  },
})
