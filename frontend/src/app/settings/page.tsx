'use client'

import { useState, useEffect } from 'react'
import { isAddress } from 'viem'
import { useConnection } from 'wagmi'
import { loadSettings, saveSettings, DEFAULT_SETTINGS, AI_PROVIDERS, INTERVALS_NO_RPC, INTERVALS_WITH_RPC, type AppSettings, type AiProvider, type RefreshInterval } from '@/lib/settings'

function AddressList({ addresses, onChange }: { addresses: string[]; onChange: (v: string[]) => void }) {
  const { address: walletAddress } = useConnection()
  const [input, setInput] = useState('')

  // 连接钱包后若列表为空，自动填入钱包地址
  useEffect(() => {
    if (walletAddress && addresses.length === 0) {
      onChange([walletAddress])
    }
  }, [walletAddress])

  const add = () => {
    const val = input.trim()
    if (!isAddress(val) || addresses.includes(val)) return
    onChange([...addresses, val])
    setInput('')
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-white">监控地址</p>
      <p className="text-xs text-gray-500">留空时监控已连接钱包，可添加多个地址</p>
      <div className="flex flex-col gap-2">
        {addresses.map(addr => (
          <div key={addr} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
            <span className="text-xs font-mono text-gray-300">{addr}</span>
            <button
              onClick={() => onChange(addresses.filter(a => a !== addr))}
              className="text-gray-600 hover:text-red-400 text-xs ml-3 shrink-0"
            >
              移除
            </button>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="0x... 添加监控地址"
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm font-mono text-gray-200 placeholder:text-gray-600 outline-none focus:border-blue-500/50"
        />
        <button
          onClick={add}
          disabled={!isAddress(input.trim())}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
        >
          添加
        </button>
      </div>
      {input && !isAddress(input.trim()) && (
        <p className="text-xs text-red-400">地址格式错误</p>
      )}
    </div>
  )
}

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      className={`relative w-11 h-6 rounded-full transition-colors ${enabled ? 'bg-blue-500' : 'bg-white/10'}`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${enabled ? 'translate-x-5' : ''}`}
      />
    </button>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white/5 border border-white/8 rounded-2xl p-6 flex flex-col gap-5">
      <h2 className="text-base font-medium text-gray-300">{title}</h2>
      {children}
    </div>
  )
}

function Row({ label, desc, children }: { label: string; desc?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-6">
      <div>
        <p className="text-sm text-white">{label}</p>
        {desc && <p className="text-xs text-gray-500 mt-0.5">{desc}</p>}
      </div>
      {children}
    </div>
  )
}


const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

export default function SettingsPage() {
  const { address: walletAddress } = useConnection()
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS)
  const [saved, setSaved] = useState(false)
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')
  const [testError, setTestError] = useState('')
  const [rpcStatus, setRpcStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')
  const [rpcError, setRpcError] = useState('')
  const [tgStatus, setTgStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')
  const [tgError, setTgError] = useState('')

  // 加载设置：优先从后端读（钱包已连接），否则用 localStorage
  useEffect(() => {
    const local = loadSettings()
    setSettings(local)
    if (!walletAddress) return
    fetch(`${BACKEND}/settings/${walletAddress}`)
      .then(r => r.json())
      .then(json => {
        if (json.ok && json.data) {
          const d = json.data
          setSettings(prev => ({
            ...prev,
            monitorEnabled: d.monitor_enabled ?? prev.monitorEnabled,
            monitorAddresses: d.monitor_addresses ?? prev.monitorAddresses,
            refreshInterval: d.refresh_interval ?? prev.refreshInterval,
            rpcUrl: d.rpc_url ?? prev.rpcUrl,
            customThresholds: {
              ...prev.customThresholds,
              enabled: d.custom_thresholds ?? prev.customThresholds.enabled,
              warningHF: d.warning_hf ?? prev.customThresholds.warningHF,
              dangerHF: d.danger_hf ?? prev.customThresholds.dangerHF,
            },
            telegram: {
              ...prev.telegram,
              chatId: d.telegram_chat_id ?? prev.telegram.chatId,
            },
            alertCooldown: {
              ...prev.alertCooldown,
              warning: d.alert_cooldown_warning ?? prev.alertCooldown.warning,
              danger: d.alert_cooldown_danger ?? prev.alertCooldown.danger,
            },
            ai: {
              ...prev.ai,
              provider: d.ai_provider ?? prev.ai.provider,
              model: d.ai_model ?? prev.ai.model,
            },
          }))
        }
      })
      .catch(() => {})
  }, [walletAddress])

  function update(patch: Partial<AppSettings>) {
    setSettings(prev => ({ ...prev, ...patch }))
    setSaved(false)
  }

  function updateThresholds(patch: Partial<AppSettings['customThresholds']>) {
    setSettings(prev => ({
      ...prev,
      customThresholds: { ...prev.customThresholds, ...patch },
    }))
    setSaved(false)
  }

  function updateTelegram(patch: Partial<AppSettings['telegram']>) {
    setSettings(prev => ({
      ...prev,
      telegram: { ...prev.telegram, ...patch },
    }))
    setSaved(false)
  }

  function updateAi(patch: Partial<AppSettings['ai']>) {
    setSettings(prev => ({
      ...prev,
      ai: { ...prev.ai, ...patch },
    }))
    setSaved(false)
  }

  async function testRpc() {
    if (!settings.rpcUrl) return
    setRpcStatus('testing')
    setRpcError('')
    try {
      const res = await fetch(`${BACKEND}/test/rpc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rpc_url: settings.rpcUrl }),
      })
      const json = await res.json()
      if (json.ok) {
        setRpcStatus('ok')
      } else {
        setRpcStatus('error')
        setRpcError(json.error ?? '连接失败')
      }
    } catch {
      setRpcStatus('error')
      setRpcError('无法连接后端服务')
    }
  }

  async function testAi() {
    setTestStatus('testing')
    setTestError('')
    try {
      const res = await fetch(`${BACKEND}/test/ai`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: settings.ai.provider, api_key: settings.ai.apiKey, model: settings.ai.model }),
      })
      const json = await res.json()
      if (json.ok) {
        setTestStatus('ok')
      } else {
        setTestStatus('error')
        setTestError(json.error ?? '连接失败')
      }
    } catch {
      setTestStatus('error')
      setTestError('无法连接后端服务')
    }
  }

  async function testTelegram() {
    if (!settings.telegram.chatId) return
    setTgStatus('testing')
    setTgError('')
    try {
      const res = await fetch(`${BACKEND}/test/telegram`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: settings.telegram.chatId }),
      })
      const json = await res.json()
      if (json.ok) {
        setTgStatus('ok')
      } else {
        setTgStatus('error')
        setTgError(json.error ?? '发送失败')
      }
    } catch {
      setTgStatus('error')
      setTgError('无法连接后端服务')
    }
  }

  async function handleSave() {
    saveSettings(settings)
    if (walletAddress) {
      try {
        await fetch(`${BACKEND}/settings/${walletAddress}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            monitor_enabled: settings.monitorEnabled,
            monitor_addresses: settings.monitorAddresses,
            refresh_interval: settings.refreshInterval,
            warning_hf: settings.customThresholds.warningHF,
            danger_hf: settings.customThresholds.dangerHF,
            custom_thresholds: settings.customThresholds.enabled,
            telegram_chat_id: settings.telegram.chatId,
            alert_cooldown_warning: settings.alertCooldown.warning,
            alert_cooldown_danger: settings.alertCooldown.danger,
            rpc_url: settings.rpcUrl,
            ai_provider: settings.ai.provider,
            ai_model: settings.ai.model,
          }),
        })
      } catch {}
    }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-10 py-10">
      <div className="w-full max-w-2xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">监控设置</h1>
          <p className="text-gray-500 text-base mt-2">自定义监控参数和通知配置</p>
        </div>

        <div className="flex flex-col gap-5">

          {/* 监控开关 */}
          <Section title="监控">
            <Row
              label="启用后台监控"
              desc="定时检查仓位健康因子，触发阈值时发送 Telegram 通知"
            >
              <Toggle
                enabled={settings.monitorEnabled}
                onChange={v => update({ monitorEnabled: v })}
              />
            </Row>
            {settings.monitorEnabled && !settings.telegram.chatId && (
              <p className="text-xs text-yellow-400">请先填写 Telegram Chat ID，否则无法接收通知</p>
            )}
            {settings.monitorEnabled && (
              <>
                <AddressList
                  addresses={settings.monitorAddresses}
                  onChange={v => update({ monitorAddresses: v })}
                />
              </>
            )}
          </Section>

          {/* 数据刷新 */}
          <Section title="监控检查频率">
            {/* RPC URL */}
            <div className="flex flex-col gap-2">
              <Row label="自定义 RPC URL" desc="填写后解锁更快检查频率（最快 30 秒）">
                <input
                  type="text"
                  value={settings.rpcUrl}
                  onChange={e => {
                    const rpcUrl = e.target.value
                    const validIntervals = rpcUrl ? INTERVALS_WITH_RPC : INTERVALS_NO_RPC
                    const currentValid = validIntervals.some(i => i.value === settings.refreshInterval)
                    update({ rpcUrl, ...(!currentValid && { refreshInterval: 300 }) })
                    setRpcStatus('idle')
                  }}
                  placeholder="https://eth-mainnet.g.alchemy.com/v2/..."
                  className="w-64 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm font-mono text-gray-200 placeholder:text-gray-600 outline-none focus:border-blue-500/50"
                />
              </Row>
              {settings.rpcUrl && (
                <div className="flex items-center gap-3">
                  <button
                    onClick={testRpc}
                    disabled={rpcStatus === 'testing'}
                    className="text-sm px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 disabled:opacity-50 transition-colors"
                  >
                    {rpcStatus === 'testing' ? '检测中…' : '测试连接'}
                  </button>
                  {rpcStatus === 'ok' && <span className="text-xs text-green-400">连接成功</span>}
                  {rpcStatus === 'error' && <span className="text-xs text-red-400">{rpcError || '连接失败'}</span>}
                </div>
              )}
              {!settings.rpcUrl && (
                <p className="text-xs text-gray-600">
                  不填也可正常使用，但检查频率限制为最快 5 分钟。
                  <a href="https://alchemy.com" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 ml-1">
                    免费注册 Alchemy →
                  </a>
                </p>
              )}
            </div>

            <Row
              label="自定义检查间隔"
              desc="关闭时使用默认值（5 分钟）"
            >
              <Toggle
                enabled={settings.customRefreshInterval}
                onChange={v => update({ customRefreshInterval: v })}
              />
            </Row>
            {settings.customRefreshInterval && (
              <div className="flex flex-col gap-2 pt-2 border-t border-white/5">
                <p className="text-xs text-gray-500">监控服务多久检查一次健康因子（仓位页面始终每 30 秒刷新）</p>
                <div className={`grid gap-2 ${settings.rpcUrl ? 'grid-cols-3' : 'grid-cols-2'}`}>
                  {(settings.rpcUrl ? INTERVALS_WITH_RPC : INTERVALS_NO_RPC).map(({ value, label }) => (
                    <button
                      key={value}
                      onClick={() => update({ refreshInterval: value as RefreshInterval })}
                      className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                        settings.refreshInterval === value
                          ? 'bg-blue-500 text-white'
                          : 'bg-white/5 text-gray-400 hover:bg-white/10'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </Section>

          {/* 警告阈值 */}
          <Section title="警告阈值">
            <Row
              label="自定义阈值"
              desc="关闭时使用加权动态阈值（稳定币更宽松，波动币更严格）"
            >
              <Toggle
                enabled={settings.customThresholds.enabled}
                onChange={v => updateThresholds({ enabled: v })}
              />
            </Row>
            <p className="text-xs text-gray-600">默认加权规则：稳定币质押 注意=1.2 / 紧急=1.05，波动币质押 注意=1.4 / 紧急=1.1</p>

            {settings.customThresholds.enabled && (
              <div className="flex flex-col gap-4 pt-2 border-t border-white/5">


                <Row label="注意线 HF" desc="低于此值显示注意">
                  <input
                    type="number"
                    min={1.01}
                    max={3}
                    step={0.01}
                    value={settings.customThresholds.warningHF}
                    onChange={e => updateThresholds({ warningHF: Number(e.target.value) })}
                    className="w-24 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white font-mono text-right outline-none focus:border-blue-500/50"
                  />
                </Row>

                <Row label="紧急线 HF" desc="低于此值显示紧急">
                  <input
                    type="number"
                    min={1.01}
                    max={3}
                    step={0.01}
                    value={settings.customThresholds.dangerHF}
                    onChange={e => updateThresholds({ dangerHF: Number(e.target.value) })}
                    className="w-24 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white font-mono text-right outline-none focus:border-blue-500/50"
                  />
                </Row>

                {settings.customThresholds.dangerHF >= settings.customThresholds.warningHF && (
                  <p className="text-xs text-red-400">紧急线必须低于注意线</p>
                )}
              </div>
            )}
          </Section>

          {/* 监控设置 */}
          <Section title="Telegram 通知">
            <Row label="Chat ID" desc="从 @userinfobot 获取你的 Telegram Chat ID">
              <input
                type="text"
                value={settings.telegram.chatId}
                onChange={e => { updateTelegram({ chatId: e.target.value }); setTgStatus('idle') }}
                placeholder="例：123456789"
                className="w-40 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm font-mono text-gray-200 placeholder:text-gray-600 outline-none focus:border-blue-500/50"
              />
            </Row>
            {settings.telegram.chatId && (
              <div className="flex items-center gap-3">
                <button
                  onClick={testTelegram}
                  disabled={tgStatus === 'testing'}
                  className="text-sm px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 disabled:opacity-50 transition-colors"
                >
                  {tgStatus === 'testing' ? '发送中…' : '发送测试消息'}
                </button>
                {tgStatus === 'ok' && <span className="text-xs text-green-400">发送成功，请检查 Telegram</span>}
                {tgStatus === 'error' && <span className="text-xs text-red-400">{tgError}</span>}
              </div>
            )}

            {/* 自定义通知间隔 */}
            <Row
              label="自定义通知间隔"
              desc="关闭时使用默认值（注意 30 分钟，紧急 5 分钟）"
            >
              <Toggle
                enabled={settings.alertCooldown.custom ?? false}
                onChange={v => setSettings(prev => ({ ...prev, alertCooldown: { ...prev.alertCooldown, custom: v } }))}
              />
            </Row>

            {settings.alertCooldown.custom && (
              <div className="flex flex-col gap-4 pt-2 border-t border-white/5">
                <div className="flex flex-col gap-2">
                  <p className="text-sm text-white">🟡 注意通知间隔</p>
                  <div className="grid grid-cols-5 gap-2">
                    {([5, 10, 30, 60, 180] as const).map(v => (
                      <button
                        key={v}
                        onClick={() => setSettings(prev => ({ ...prev, alertCooldown: { ...prev.alertCooldown, warning: v } }))}
                        className={`py-1.5 rounded-lg text-sm transition-colors ${
                          settings.alertCooldown.warning === v
                            ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                            : 'bg-white/5 text-gray-400 hover:bg-white/10'
                        }`}
                      >
                        {v < 60 ? `${v} 分钟` : `${v/60} 小时`}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <p className="text-sm text-white">🔴 紧急通知间隔</p>
                  <div className="grid grid-cols-4 gap-2">
                    {([2, 5, 10, 30] as const).map(v => (
                      <button
                        key={v}
                        onClick={() => setSettings(prev => ({ ...prev, alertCooldown: { ...prev.alertCooldown, danger: v } }))}
                        className={`py-1.5 rounded-lg text-sm transition-colors ${
                          settings.alertCooldown.danger === v
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : 'bg-white/5 text-gray-400 hover:bg-white/10'
                        }`}
                      >
                        {v} 分钟
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

          </Section>

          {/* AI 分析 */}
          <Section title="AI 分析">
            <p className="text-xs text-gray-500 mb-2">AI Key 用于对话分析，监控告警由平台提供。</p>
            {/* 提供商选择 */}
            <Row label="AI 提供商" desc="选择你拥有 API Key 的服务商">
              <select
                value={settings.ai.provider}
                onChange={e => {
                  const provider = e.target.value as AiProvider
                  updateAi({
                    provider,
                    model: '',
                    apiKey: '',
                  })
                }}
                className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-gray-200 outline-none focus:border-blue-500/50"
              >
                {(Object.keys(AI_PROVIDERS) as AiProvider[]).map(p => (
                  <option key={p} value={p} className="bg-gray-900">
                    {AI_PROVIDERS[p].label}
                  </option>
                ))}
              </select>
            </Row>

            {/* API Key */}
            {(() => {
              const cfg = AI_PROVIDERS[settings.ai.provider]
              const keyInvalid = settings.ai.apiKey.length > 0 && !cfg.validate(settings.ai.apiKey)
              return (
                <Row label="API Key" desc="存储在本地，不会上传">
                  <div className="flex flex-col items-end gap-1">
                    <input
                      type="password"
                      value={settings.ai.apiKey}
                      onChange={e => updateAi({ apiKey: e.target.value })}
                      placeholder={cfg.keyPlaceholder}
                      className={`w-52 bg-white/5 border rounded-lg px-3 py-1.5 text-sm font-mono text-gray-200 placeholder:text-gray-600 outline-none transition-colors ${
                        keyInvalid ? 'border-red-500/60' : 'border-white/10 focus:border-blue-500/50'
                      }`}
                    />
                    {keyInvalid && (
                      <span className="text-xs text-red-400">
                        Key 格式与 {cfg.label} 不匹配
                      </span>
                    )}
                  </div>
                </Row>
              )
            })()}

            {/* 模型 ID */}
            {(() => {
              const cfg = AI_PROVIDERS[settings.ai.provider]
              return (
                <div className="flex flex-col gap-2">
                  <Row label="模型 ID" desc="填写官方模型 ID，不是产品名称">
                    <input
                      type="text"
                      value={settings.ai.model}
                      onChange={e => updateAi({ model: e.target.value })}
                      placeholder="在官方文档中查找模型 ID"
                      className="w-52 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm font-mono text-gray-200 placeholder:text-gray-600 outline-none focus:border-blue-500/50"
                    />
                  </Row>
                  <a
                    href={cfg.docsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 pl-1"
                  >
                    查看 {cfg.label} 官方模型列表 →
                  </a>
                </div>
              )
            })()}

            {/* 测试连接 */}
            <div className="flex items-center gap-3 pt-1">
              <button
                onClick={testAi}
                disabled={!settings.ai.apiKey || !settings.ai.model || testStatus === 'testing'}
                className="px-4 py-1.5 rounded-lg text-sm bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {testStatus === 'testing' ? '测试中...' : '测试连接'}
              </button>
              {testStatus === 'ok' && <span className="text-xs text-green-400">连接成功</span>}
              {testStatus === 'error' && <span className="text-xs text-red-400">{testError}</span>}
            </div>

          </Section>

          {/* 保存按钮 */}
          <button
            onClick={handleSave}
            className={`w-full py-3 rounded-xl text-sm font-medium transition-all ${
              saved
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
            {saved ? '已保存' : '保存设置'}
          </button>
        </div>
      </div>
    </div>
  )
}
