'use client'

import { useState, useEffect, useRef } from 'react'
import { isAddress } from 'viem'
import { useConnection } from 'wagmi'
import { ClientOnly } from '@/components/ClientOnly'
import { usePosition } from '@/hooks/usePosition'
import { loadSettings } from '@/lib/settings'
import ReactMarkdown from 'react-markdown'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

// ─── 类型 ────────────────────────────────────────────────────────────────────

type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

type Conversation = {
  id: string
  title: string
  updated_at: string
  messages: Message[]
}

// ─── 后端 API ─────────────────────────────────────────────────────────────────

async function apiListConversations(wallet: string): Promise<Conversation[]> {
  try {
    const res = await fetch(`${BACKEND}/chat/${wallet}`)
    const json = await res.json()
    return (json.data ?? []).map((c: { id: string; title: string; updated_at: string }) => ({ ...c, messages: [] }))
  } catch { return [] }
}

async function apiCreateConversation(wallet: string, title: string): Promise<Conversation | null> {
  try {
    const res = await fetch(`${BACKEND}/chat/${wallet}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
    const json = await res.json()
    return json.ok ? { ...json.data, messages: [] } : null
  } catch { return null }
}

async function apiDeleteConversation(wallet: string, id: string): Promise<void> {
  try {
    await fetch(`${BACKEND}/chat/${wallet}/${id}`, { method: 'DELETE' })
  } catch {}
}

async function apiLoadMessages(wallet: string, id: string): Promise<Message[]> {
  try {
    const res = await fetch(`${BACKEND}/chat/${wallet}/${id}`)
    const json = await res.json()
    return json.data ?? []
  } catch { return [] }
}

async function apiAddMessage(wallet: string, convId: string, role: string, content: string): Promise<Message | null> {
  try {
    const res = await fetch(`${BACKEND}/chat/${wallet}/${convId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, content }),
    })
    const json = await res.json()
    return json.ok ? json.data : null
  } catch { return null }
}

function formatDate(ts: string): string {
  const d = new Date(ts)
  const now = new Date()
  const diff = now.getDate() - d.getDate()
  if (diff === 0 && now.getMonth() === d.getMonth()) return '今天'
  if (diff === 1) return '昨天'
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// ─── 常量 ────────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  { icon: '🛡️', text: '我的仓位现在安全吗？' },
  { icon: '📏', text: '我距离清算还有多远？' },
  { icon: '💰', text: '我应该补充多少抵押品？' },
  { icon: '📊', text: '分析一下我的仓位结构' },
]

// ─── 后端 Agent 调用 ──────────────────────────────────────────────────────────


// ─── HF 徽章 ─────────────────────────────────────────────────────────────────

function PositionBadge({ address }: { address: `0x${string}` }) {
  const { position } = usePosition(address)
  if (!position) return null
  const hf = position.noDebt ? null : position.health
  const color = !hf ? 'text-blue-400 border-blue-500/30 bg-blue-500/10'
    : hf >= 1.4 ? 'text-green-400 border-green-500/30 bg-green-500/10'
    : hf >= 1.1 ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10'
    : 'text-red-400 border-red-500/30 bg-red-500/10'
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono ${color}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      <span>HF {position.noDebt ? '∞' : position.health.toFixed(3)}</span>
      <span className="opacity-40">·</span>
      <span className="opacity-70">已获取仓位上下文</span>
    </div>
  )
}

// ─── 对话列表侧栏 ─────────────────────────────────────────────────────────────

function ConversationSidebar({
  history, activeId, onSelect, onNew, onDelete,
}: {
  history: Conversation[]
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}) {
  const grouped: { label: string; items: Conversation[] }[] = []
  const seen = new Set<string>()
  history.forEach(conv => {
    const label = formatDate(conv.updated_at)
    if (!seen.has(label)) { seen.add(label); grouped.push({ label, items: [] }) }
    grouped.find(g => g.label === label)!.items.push(conv)
  })

  return (
    <div className="w-56 shrink-0 h-screen flex flex-col border-r border-white/5 bg-black/20">
      {/* 新对话按钮 */}
      <div className="px-3 py-4 border-b border-white/5">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/8 text-gray-300 hover:text-white text-sm font-medium transition-colors"
        >
          <span className="text-lg leading-none text-blue-400">+</span>
          新对话
        </button>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto py-2">
        {history.length === 0 && (
          <p className="text-xs text-gray-600 px-4 py-6 text-center">暂无历史对话</p>
        )}
        {grouped.map(group => (
          <div key={group.label} className="mb-2">
            <p className="text-xs text-gray-700 px-4 pt-3 pb-1 font-medium uppercase tracking-wider">{group.label}</p>
            {group.items.map(conv => (
              <div
                key={conv.id}
                className={`group flex items-start gap-2 mx-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                  conv.id === activeId
                    ? 'bg-white/8 text-white'
                    : 'text-gray-500 hover:bg-white/5 hover:text-gray-300'
                }`}
                onClick={() => onSelect(conv.id)}
              >
                <div className="flex-1 min-w-0 pt-0.5">
                  <p className="text-xs font-medium truncate">{conv.title}</p>
                  {conv.messages.length > 0 && (
                    <p className="text-xs text-gray-700 truncate mt-0.5">
                      {conv.messages[conv.messages.length - 1].content.slice(0, 22)}…
                    </p>
                  )}
                </div>
                <button
                  onClick={e => { e.stopPropagation(); onDelete(conv.id) }}
                  className="shrink-0 opacity-0 group-hover:opacity-100 mt-0.5 text-gray-600 hover:text-red-400 transition-all text-xs"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── 主对话区 ─────────────────────────────────────────────────────────────────

function ChatArea({
  conversation, address, wallet, onChange,
}: {
  conversation: Conversation
  address: `0x${string}`
  wallet: string
  onChange: (conv: Conversation) => void
}) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation.messages, loading])

  function cancel() {
    abortRef.current?.abort()
  }

  async function send(text: string) {
    if (!text.trim() || loading) return

    const tempUserMsg: Message = { id: `tmp-${Date.now()}`, role: 'user', content: text.trim() }
    const updatedMessages = [...conversation.messages, tempUserMsg]
    const title = conversation.messages.length === 0
      ? text.trim().slice(0, 18) + (text.length > 18 ? '…' : '')
      : conversation.title

    // 立即插入空的 AI 气泡（流式内容会填入）
    const aiMsgId = `ai-${Date.now()}`
    const withPlaceholder: Message[] = [...updatedMessages, { id: aiMsgId, role: 'assistant', content: '' }]
    onChange({ ...conversation, title, messages: withPlaceholder })
    setInput('')
    setLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    if (wallet) await apiAddMessage(wallet, conversation.id, 'user', text.trim())

    const settings = loadSettings()
    const { apiKey, model, provider } = settings.ai

    if (!apiKey || !model) {
      const errContent = '请先在设置页填写 AI 提供商和 API Key，才能使用对话功能。'
      onChange({ ...conversation, title, messages: withPlaceholder.map(m => m.id === aiMsgId ? { ...m, content: errContent } : m) })
      setLoading(false)
      return
    }

    const timeout = AbortSignal.timeout(120000)
    const combined = AbortSignal.any([controller.signal, timeout])
    let fullContent = ''

    try {
      const res = await fetch(`${BACKEND}/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: updatedMessages.slice(-10).map(m => ({ role: m.role, content: m.content })),
          api_key: apiKey,
          model,
          provider,
          rpc_url: settings.rpcUrl || null,
          wallet_address: address || null,
        }),
        signal: combined,
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))
          if (data.text) {
            fullContent += data.text
            onChange({ ...conversation, title, messages: withPlaceholder.map(m => m.id === aiMsgId ? { ...m, content: fullContent } : m) })
          } else if (data.error) {
            throw new Error(data.error)
          }
        }
      }

      if (wallet && fullContent) await apiAddMessage(wallet, conversation.id, 'assistant', fullContent)
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') return
      const errContent = `请求出错：${e instanceof Error ? e.message : '请求失败'}`
      onChange({ ...conversation, title, messages: withPlaceholder.map(m => m.id === aiMsgId ? { ...m, content: errContent } : m) })
    } finally {
      abortRef.current = null
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col h-screen min-w-0">
      {/* 顶部栏 */}
      <div className="flex items-center justify-between px-8 py-4 border-b border-white/5 shrink-0">
        <p className="text-sm font-medium text-gray-300">{conversation.title}</p>
        <ClientOnly>
          <PositionBadge address={address} />
        </ClientOnly>
      </div>

      {/* 消息区 */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
          {conversation.messages.length === 0 && (
            <div className="flex flex-col items-center gap-8 py-16 text-center">
              <div className="relative">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/20 flex items-center justify-center text-4xl">◉</div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-green-500 border-2 border-black flex items-center justify-center">
                  <span className="text-white text-xs leading-none">✓</span>
                </div>
              </div>
              <div>
                <p className="text-white text-xl font-semibold mb-2">AI 仓位分析助手</p>
                <p className="text-gray-500 text-sm">已读取实时仓位数据，随时可以提问</p>
              </div>
              <div className="grid grid-cols-2 gap-3 w-full">
                {SUGGESTIONS.map(s => (
                  <button
                    key={s.text}
                    onClick={() => send(s.text)}
                    className="text-left px-4 py-4 rounded-xl bg-white/4 border border-white/8 hover:bg-white/8 hover:border-white/15 transition-all group"
                  >
                    <span className="text-xl block mb-1.5">{s.icon}</span>
                    <span className="text-sm text-gray-400 group-hover:text-gray-200 transition-colors">{s.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {conversation.messages.map(msg => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gradient-to-br from-blue-500/30 to-purple-500/30 border border-blue-500/20 text-blue-400'
              }`}>
                {msg.role === 'user' ? '你' : '◉'}
              </div>
              <div className={`max-w-[78%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-sm'
                  : 'bg-white/5 border border-white/8 text-gray-200 rounded-tl-sm'
              }`}>
                {msg.role === 'assistant'
                  ? <div className="prose prose-invert prose-sm max-w-none"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                  : msg.content}
              </div>
            </div>
          ))}

          {loading && conversation.messages.at(-1)?.content === '' && (
            <div className="flex gap-3">
              <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500/30 to-purple-500/30 border border-blue-500/20 text-blue-400 flex items-center justify-center text-xs">◉</div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white/5 border border-white/8 flex flex-col gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-xs text-gray-500 animate-pulse">正在查询数据并分析…</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* 输入区 */}
      <div className="shrink-0 px-6 pb-6 pt-4 border-t border-white/5">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-3 items-center bg-white/5 border border-white/10 rounded-2xl px-4 py-3 focus-within:border-blue-500/40 transition-colors">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) }
              }}
              placeholder="问问 AI 你的仓位风险…"
              rows={1}
              className="flex-1 bg-transparent text-sm text-gray-200 placeholder:text-gray-600 outline-none resize-none"
            />
            <div className="flex items-center gap-2 shrink-0">
              {!loading && <span className="text-xs text-gray-700">Enter 发送</span>}
              {loading ? (
                <button
                  onClick={cancel}
                  className="w-8 h-8 rounded-xl bg-red-600/80 hover:bg-red-500 text-white flex items-center justify-center transition-colors"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="4" y="4" width="16" height="16" rx="2" />
                  </svg>
                </button>
              ) : (
                <button
                  onClick={() => send(input)}
                  disabled={!input.trim()}
                  className="w-8 h-8 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── 无地址提示 ───────────────────────────────────────────────────────────────

function NoAddress() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-5 text-center">
      <div className="w-20 h-20 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-4xl">◉</div>
      <div>
        <h2 className="text-xl font-bold text-white mb-2">需要先查询仓位</h2>
        <p className="text-gray-500 text-sm max-w-xs">请先在仓位页面输入地址或连接钱包，AI 才能获取你的仓位数据。</p>
      </div>
    </div>
  )
}

// ─── 页面 ─────────────────────────────────────────────────────────────────────

function ChatPageContent() {
  const { address: walletAddress, isConnected } = useConnection()
  const [address, setAddress] = useState('')
  const [history, setHistory] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState('')

  const wallet = walletAddress ?? ''

  useEffect(() => {
    setAddress(localStorage.getItem('queryAddress') ?? '')
  }, [])

  // 加载对话列表（依赖 isConnected，确保 wagmi 重连后也能触发）
  useEffect(() => {
    if (!wallet || !isConnected) return
    apiListConversations(wallet).then(convs => {
      if (convs.length > 0) { setHistory(convs); setActiveId(convs[0].id) }
    })
  }, [wallet, isConnected])

  // 切换对话时加载消息
  useEffect(() => {
    if (!wallet || !activeId) return
    apiLoadMessages(wallet, activeId).then(msgs => {
      setHistory(prev => prev.map(c => c.id === activeId ? { ...c, messages: msgs } : c))
    })
  }, [activeId, wallet])

  const queryAddress = (isAddress(address) ? address : wallet) as `0x${string}` | undefined

  async function handleNew() {
    if (!wallet) return
    const c = await apiCreateConversation(wallet, '新对话')
    if (!c) return
    setHistory(prev => [c, ...prev])
    setActiveId(c.id)
  }

  async function handleDelete(id: string) {
    if (wallet) await apiDeleteConversation(wallet, id)
    setHistory(prev => {
      const updated = prev.filter(c => c.id !== id)
      if (activeId === id && updated.length > 0) setActiveId(updated[0].id)
      return updated
    })
  }

  function handleChange(conv: Conversation) {
    setHistory(prev => prev.map(c => c.id === conv.id ? conv : c))
  }

  const active = history.find(c => c.id === activeId)

  if (!isConnected) return (
    <div className="flex h-screen items-center justify-center text-center flex-col gap-4">
      <div className="text-4xl">🔌</div>
      <p className="text-gray-300 text-lg font-medium">请先连接钱包</p>
      <p className="text-gray-600 text-sm">对话历史需要绑定钱包地址</p>
    </div>
  )

  return (
    <div className="flex h-screen">
      <ConversationSidebar
        history={history}
        activeId={activeId}
        onSelect={id => { setActiveId(id) }}
        onNew={handleNew}
        onDelete={handleDelete}
      />
      {queryAddress
        ? active && <ChatArea key={activeId} conversation={active} address={queryAddress} wallet={wallet} onChange={handleChange} />
        : <NoAddress />
      }
    </div>
  )
}

export default function ChatPage() {
  return <ClientOnly><ChatPageContent /></ClientOnly>
}
