export type RefreshInterval = 30 | 60 | 300 | 1800 | 3600 | 10800

// 没有自定义 RPC 时可选的间隔
export const INTERVALS_NO_RPC: { value: RefreshInterval; label: string }[] = [
  { value: 300,   label: '5 分钟' },
  { value: 1800,  label: '30 分钟' },
  { value: 3600,  label: '1 小时' },
  { value: 10800, label: '3 小时' },
]

// 有自定义 RPC 时可选的间隔
export const INTERVALS_WITH_RPC: { value: RefreshInterval; label: string }[] = [
  { value: 30,    label: '30 秒' },
  { value: 60,    label: '1 分钟' },
  { value: 300,   label: '5 分钟' },
  { value: 1800,  label: '30 分钟' },
  { value: 3600,  label: '1 小时' },
  { value: 10800, label: '3 小时' },
]

export type AiProvider = 'anthropic' | 'openai' | 'google' | 'deepseek' | 'doubao'

export interface AiProviderConfig {
  label: string
  keyPlaceholder: string
  validate: (key: string) => boolean
  docsUrl: string
}

export const AI_PROVIDERS: Record<AiProvider, AiProviderConfig> = {
  anthropic: {
    label: 'Anthropic Claude',
    keyPlaceholder: 'sk-ant-...',
    validate: (k) => k.startsWith('sk-ant-'),
    docsUrl: 'https://docs.anthropic.com/en/docs/about-claude/models',
  },
  openai: {
    label: 'OpenAI',
    keyPlaceholder: 'sk-...',
    validate: (k) => k.startsWith('sk-') && !k.startsWith('sk-ant-'),
    docsUrl: 'https://platform.openai.com/docs/models',
  },
  google: {
    label: 'Google Gemini',
    keyPlaceholder: 'AIza...',
    validate: (k) => k.startsWith('AIza'),
    docsUrl: 'https://ai.google.dev/gemini-api/docs/models',
  },
  deepseek: {
    label: 'DeepSeek',
    keyPlaceholder: 'sk-...',
    validate: (k) => k.startsWith('sk-') && !k.startsWith('sk-ant-'),
    docsUrl: 'https://api-docs.deepseek.com/quick_start/pricing',
  },
  doubao: {
    label: '豆包 (火山引擎)',
    keyPlaceholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
    validate: (k) => k.length > 10,
    docsUrl: 'https://www.volcengine.com/docs/82379/1330310',
  },
}

export interface AppSettings {
  monitorEnabled: boolean
  monitorAddresses: string[]
  rpcUrl: string
  customRefreshInterval: boolean
  refreshInterval: RefreshInterval
  alertCooldown: {
    custom: boolean
    warning: number  // 分钟
    danger: number   // 分钟
  }
  customThresholds: {
    enabled: boolean
    warningHF: number
    dangerHF: number
  }
  telegram: {
    chatId: string
  }
  ai: {
    provider: AiProvider
    apiKey: string
    model: string
  }
}

export const DEFAULT_SETTINGS: AppSettings = {
  monitorEnabled: false,
  monitorAddresses: [],
  rpcUrl: '',
  customRefreshInterval: false,
  refreshInterval: 300,
  alertCooldown: {
    custom: false,
    warning: 30,
    danger: 5,
  },
  customThresholds: {
    enabled: false,
    warningHF: 1.4,
    dangerHF: 1.1,
  },
  telegram: {
    chatId: '',
  },
  ai: {
    provider: 'anthropic',
    apiKey: '',
    model: '',
  },
}

// 根据抵押品构成计算加权警告阈值，与后端 monitor.py 保持一致
export function computeWeightedThresholds(collateral: { valueUsd: number; isStable: boolean }[]): { warningHF: number; dangerHF: number } {
  const totalValue = collateral.reduce((s, t) => s + t.valueUsd, 0)
  if (totalValue === 0) return { warningHF: 1.4, dangerHF: 1.1 }
  const warningHF = collateral.reduce((s, t) => s + (t.valueUsd / totalValue) * (t.isStable ? 1.2 : 1.4), 0)
  const dangerHF  = collateral.reduce((s, t) => s + (t.valueUsd / totalValue) * (t.isStable ? 1.05 : 1.1), 0)
  return { warningHF, dangerHF }
}

export function loadSettings(): AppSettings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS
  try {
    const raw = localStorage.getItem('appSettings')
    if (!raw) return DEFAULT_SETTINGS
    const parsed = JSON.parse(raw) as Partial<AppSettings>
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      alertCooldown: { ...DEFAULT_SETTINGS.alertCooldown, ...parsed.alertCooldown },
      customThresholds: { ...DEFAULT_SETTINGS.customThresholds, ...parsed.customThresholds },
      telegram: { ...DEFAULT_SETTINGS.telegram, ...parsed.telegram },
      ai: { ...DEFAULT_SETTINGS.ai, ...parsed.ai },
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

export function saveSettings(s: AppSettings) {
  localStorage.setItem('appSettings', JSON.stringify(s))
}
