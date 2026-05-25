'use client'

interface TrustScoreProps {
  value: number
}

export function TrustScore({ value }: TrustScoreProps) {
  const clamped = Math.max(0, Math.min(10, value))

  const color =
    clamped >= 6
      ? 'text-green-400'
      : clamped >= 3
        ? 'text-amber-400'
        : 'text-red-400'

  const label =
    clamped >= 6 ? 'Trusting' : clamped >= 3 ? 'Guarded' : 'Disengaged'

  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-muted-foreground">Trust Score</span>
      <div className="flex items-center gap-2">
        <span className={`text-sm font-semibold tabular-nums ${color}`}>
          {clamped.toFixed(1)}
        </span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}