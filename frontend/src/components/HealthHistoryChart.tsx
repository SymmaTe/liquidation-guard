'use client'

import { useEffect, useState } from 'react'
import { useConnection } from 'wagmi'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

const RANGES = [
  { label: '2h',  days: 2 / 24 },
  { label: '24h', days: 1 },
  { label: '3d',  days: 3 },
  { label: '7d',  days: 7 },
]

interface HistoryPoint {
  health_factor: number
  collateral_usd: number
  debt_usd: number
  alert_level: string
  recorded_at: string
}

function formatTime(iso: string, days: number) {
  const d = new Date(iso)
  if (days <= 1) return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:00`
}

function dotColor(hf: number) {
  if (hf >= 1.4) return '#22c55e'
  if (hf >= 1.1) return '#eab308'
  return '#ef4444'
}

const CustomDot = (props: any) => {
  const { cx, cy, payload } = props
  if (payload.hf === null || payload.hf === undefined) return null
  return <circle cx={cx} cy={cy} r={3} fill={dotColor(payload.hf)} stroke="none" />
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  if (d.hf === null) return null
  return (
    <div className="bg-[#1a1a2e] border border-white/10 rounded-xl px-3 py-2 text-xs space-y-1">
      <p className="text-gray-400">{d.time}</p>
      <p className="text-white font-mono">HF {d.hf.toFixed(3)}</p>
      <p className="text-gray-400">抵押 ${d.collateral.toLocaleString()}</p>
      <p className="text-gray-400">借款 ${d.debt.toLocaleString()}</p>
    </div>
  )
}

export function HealthHistoryChart({ address }: { address: `0x${string}` }) {
  const { address: wallet } = useConnection()
  const [data, setData] = useState<HistoryPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [warningHf, setWarningHf] = useState(1.4)
  const [dangerHf, setDangerHf] = useState(1.1)
  const [rangeDays, setRangeDays] = useState<number>(() => {
    if (typeof window === 'undefined') return 1
    return Number(localStorage.getItem('chartRange') ?? 2 / 24)
  })

  useEffect(() => {
    const load = () => {
      fetch(`${BACKEND}/history/${address}?days=7`)
        .then(r => r.json())
        .then(j => { if (j.ok) setData(j.data) })
        .finally(() => setLoading(false))
    }
    setLoading(true)
    load()
    const timer = setInterval(load, 5 * 60 * 1000)
    return () => clearInterval(timer)
  }, [address])

  useEffect(() => {
    if (!wallet) return
    fetch(`${BACKEND}/settings/${wallet}`)
      .then(r => r.json())
      .then(j => {
        if (j.ok && j.data) {
          setWarningHf(j.data.warning_hf ?? 1.4)
          setDangerHf(j.data.danger_hf ?? 1.1)
        }
      })
  }, [wallet])

  const handleRange = (days: number) => {
    setRangeDays(days)
    localStorage.setItem('chartRange', String(days))
  }

  if (loading) return null
  if (data.length < 1) return null

  // 将选定时间窗口分成 24 个桶
  const BUCKETS = 24
  const now = Date.now()
  const windowMs = rangeDays * 24 * 60 * 60 * 1000
  const bucketMs = windowMs / BUCKETS
  const start = now - windowMs

  const chartData = Array.from({ length: BUCKETS }, (_, i) => {
    const bucketStart = start + i * bucketMs
    const bucketEnd = bucketStart + bucketMs
    const bucketLabel = formatTime(new Date(bucketStart).toISOString(), rangeDays)

    const points = data.filter(d => {
      const t = new Date(d.recorded_at).getTime()
      return t >= bucketStart && t < bucketEnd && d.health_factor <= 100
    })

    if (points.length === 0) return { time: bucketLabel, hf: null, collateral: 0, debt: 0 }

    const avg = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length
    return {
      time: bucketLabel,
      hf: Math.round(avg(points.map(d => d.health_factor)) * 1000) / 1000,
      collateral: Math.round(avg(points.map(d => d.collateral_usd))),
      debt: Math.round(avg(points.map(d => d.debt_usd))),
    }
  })

  const hfValues = chartData.map(d => d.hf).filter((v): v is number => v !== null)
  const hasData = hfValues.length >= 1
  const minHf = hasData ? Math.min(...hfValues) : 1
  const maxHf = hasData ? Math.max(...hfValues) : 2
  const yMin = Math.max(0, Math.floor((minHf - 0.2) * 10) / 10)
  const yMax = Math.ceil((maxHf + 0.2) * 10) / 10

  return (
    <div className="bg-white/3 border border-white/8 rounded-2xl p-5">
      <h3 className="text-sm font-medium text-gray-300 mb-4">健康度走势</h3>
      {hasData ? (
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: '#6b7280' }}
              tickLine={false}
              axisLine={false}
              interval={1}
            />
            <YAxis
              domain={[yMin, yMax]}
              tick={{ fontSize: 10, fill: '#6b7280' }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => v.toFixed(1)}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={warningHf} stroke="#22c55e" strokeDasharray="4 4" strokeOpacity={0.4} />
            <ReferenceLine y={dangerHf} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.4} />
            <Line
              type="monotone"
              dataKey="hf"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={<CustomDot />}
              activeDot={{ r: 5, fill: '#3b82f6' }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-xs text-gray-600 text-center py-8">该时间段内暂无监控数据</p>
      )}
      <div className="flex items-center justify-between mt-3">
        <div className="flex gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-1.5"><span className="w-3 h-px bg-green-500 inline-block" /> 安全线 {warningHf}</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-px bg-yellow-500 inline-block" /> 注意线 {dangerHf}</span>
        </div>
        <div className="flex gap-1">
          {RANGES.map(r => (
            <button
              key={r.label}
              onClick={() => handleRange(r.days)}
              className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${
                rangeDays === r.days
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'text-gray-600 hover:text-gray-400'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
