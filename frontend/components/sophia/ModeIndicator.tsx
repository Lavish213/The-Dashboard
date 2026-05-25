'use client'

import { useSophiaStore } from '@/stores/sophia.store'

export function ModeIndicator() {
  const mode = useSophiaStore((s) => s.mode)

  if (mode === 'human_takeover') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        Human Active
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-500/25 bg-teal-500/10 px-2.5 py-0.5 text-xs font-semibold text-teal-400">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-400" />
      AI Active
    </span>
  )
}