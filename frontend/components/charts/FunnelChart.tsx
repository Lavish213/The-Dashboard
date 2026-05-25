'use client'

import { useEffect, useRef, useState } from 'react'

interface FunnelBar {
  label: string
  value: number
  max: number
  color: string
}

interface FunnelChartProps {
  bars: FunnelBar[]
}

function AnimatedBar({ bar, delay }: { bar: FunnelBar; delay: number }) {
  const [width, setWidth] = useState(0)
  const pct = bar.max > 0 ? (bar.value / bar.max) * 100 : 0

  useEffect(() => {
    const t = setTimeout(() => setWidth(pct), delay)
    return () => clearTimeout(t)
  }, [pct, delay])

  return (
    <div className="flex items-center gap-3">
      <div className="w-20 flex-shrink-0 text-xs text-muted-foreground text-right">
        {bar.label}
      </div>
      <div className="flex-1 h-5 bg-muted rounded overflow-hidden relative">
        <div
          className={`h-full rounded ${bar.color} transition-all duration-700 ease-out flex items-center px-2`}
          style={{ width: `${width}%` }}
        >
          {width > 20 && (
            <span className="text-xs font-semibold text-white tabular-nums">
              {bar.value}
            </span>
          )}
        </div>
        {width <= 20 && bar.value > 0 && (
          <span className="absolute right-0 top-0 h-full flex items-center pr-2 text-xs text-muted-foreground tabular-nums">
            {bar.value}
          </span>
        )}
      </div>
    </div>
  )
}

export function FunnelChart({ bars }: FunnelChartProps) {
  return (
    <div className="space-y-2">
      {bars.map((bar, i) => (
        <AnimatedBar key={bar.label} bar={bar} delay={i * 80} />
      ))}
    </div>
  )
}