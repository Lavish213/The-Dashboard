'use client'

interface DealHeatGaugeProps {
  value: number
}

export function DealHeatGauge({ value }: DealHeatGaugeProps) {
  const clamped = Math.max(0, Math.min(10, value))
  const pct = (clamped / 10) * 100

  const color =
    clamped >= 7
      ? 'bg-green-500'
      : clamped >= 4
        ? 'bg-amber-500'
        : 'bg-red-500'

  const label =
    clamped >= 7 ? 'Hot' : clamped >= 4 ? 'Warm' : 'Cold'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Deal Heat</span>
        <span className="font-semibold tabular-nums text-foreground">
          {clamped.toFixed(1)} <span className="text-muted-foreground font-normal">/ 10</span>
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-right text-xs text-muted-foreground">{label}</div>
    </div>
  )
}