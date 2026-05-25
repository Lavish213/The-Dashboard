'use client'

function getInitials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()
}

function getNameColor(name: string): string {
  const colors = [
    'bg-teal-500/20 text-teal-400',
    'bg-blue-500/20 text-blue-400',
    'bg-purple-500/20 text-purple-400',
    'bg-amber-500/20 text-amber-400',
    'bg-rose-500/20 text-rose-400',
    'bg-emerald-500/20 text-emerald-400',
  ]
  const index = name.charCodeAt(0) % colors.length
  return colors[index]
}

function scoreRingColor(score: number | null): string {
  if (!score) return 'ring-border'
  if (score >= 7) return 'ring-green-500/60'
  if (score >= 4) return 'ring-amber-500/60'
  return 'ring-red-500/60'
}

interface AvatarScoreProps {
  name: string
  score?: number | null
  size?: 'sm' | 'md' | 'lg'
}

export function AvatarScore({ name, score, size = 'md' }: AvatarScoreProps) {
  const initials = getInitials(name)
  const colorClass = getNameColor(name)
  const ringColor = scoreRingColor(score ?? null)

  const sizeClasses = {
    sm: 'h-7 w-7 text-xs',
    md: 'h-9 w-9 text-sm',
    lg: 'h-11 w-11 text-base',
  }

  return (
    <div
      className={`rounded-full flex items-center justify-center font-semibold flex-shrink-0 ring-2 ${sizeClasses[size]} ${colorClass} ${ringColor}`}
    >
      {initials}
    </div>
  )
}