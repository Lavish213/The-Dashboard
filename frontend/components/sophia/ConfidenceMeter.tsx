'use client'

interface ConfidenceMeterProps {
  value: number
  handoffRecommended: boolean
}

export function ConfidenceMeter({ value, handoffRecommended }: ConfidenceMeterProps) {
  const clamped = Math.max(0, Math.min(1, value))
  const pct = clamped * 100

  const color = handoffRecommended
    ? 'bg-red-500'
    : clamped >= 0.6
      ? 'bg-green-500'
      : 'bg-amber-500'

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Sophia Confidence</span>
        <span className="font-semibold tabular-nums text-foreground">
          {Math.round(pct)}%
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {handoffRecommended && (
        <p className="text-xs text-red-400">Handoff recommended</p>
      )}
    </div>
  )
}