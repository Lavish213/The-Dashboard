export const SCORE_COLORS = {
  high: { text: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20' },
  mid: { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
  low: { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
} as const

export function scoreColor(score: number | null) {
  if (!score) return SCORE_COLORS.low
  if (score >= 7) return SCORE_COLORS.high
  if (score >= 4) return SCORE_COLORS.mid
  return SCORE_COLORS.low
}

export const STATUS_COLORS: Record<string, string> = {
  new: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  contacted: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  qualified: 'bg-green-500/10 text-green-400 border-green-500/20',
  disqualified: 'bg-red-500/10 text-red-400 border-red-500/20',
  converted: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  dead: 'bg-muted text-muted-foreground border-border',
  pending: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  active: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  completed: 'bg-green-500/10 text-green-400 border-green-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  cancelled: 'bg-muted text-muted-foreground border-border',
  paused: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  initiated: 'bg-muted text-muted-foreground border-border',
  ringing: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  connected: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  no_answer: 'bg-muted text-muted-foreground border-border',
  voicemail: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

export const CALL_STATUS_COLORS: Record<string, string> = {
  initiated: 'bg-muted text-muted-foreground border-border',
  ringing: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  connected: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  completed: 'bg-green-500/10 text-green-400 border-green-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  no_answer: 'bg-muted text-muted-foreground border-border',
  voicemail: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

export const GOLD = '#E6C27A'
export const TEAL = '#5FCFCB'

export const SOPHIA_ACTIVE = 'border-teal-500/30 bg-teal-500/5'
export const SOPHIA_TAKEOVER = 'border-amber-500/30 bg-amber-500/5'

export const HIGH_SCORE_BORDER = 'border-gold/30'
export const HIGH_SCORE_BG = 'bg-gold/5'