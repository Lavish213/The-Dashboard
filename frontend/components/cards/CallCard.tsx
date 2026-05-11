import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Phone, PhoneOff, PhoneMissed, Clock, Mic } from 'lucide-react'

export type CallOutcome =
  | 'completed'
  | 'missed'
  | 'voicemail'
  | 'failed'
  | 'in-progress'

export interface CallCardProps {
  id: string
  contactName: string
  contactPhone?: string
  direction: 'inbound' | 'outbound'
  outcome: CallOutcome
  duration?: string
  startedAt?: string
  agent?: string
  score?: number
  summary?: string
  className?: string
  onClick?: () => void
}

const outcomeIcon: Record<CallOutcome, React.ReactNode> = {
  completed: <Phone className="h-3.5 w-3.5" />,
  missed: <PhoneMissed className="h-3.5 w-3.5" />,
  voicemail: <Mic className="h-3.5 w-3.5" />,
  failed: <PhoneOff className="h-3.5 w-3.5" />,
  'in-progress': <Phone className="h-3.5 w-3.5 animate-pulse" />,
}

const outcomeBadge: Record<CallOutcome, string> = {
  completed: 'completed',
  missed: 'failed',
  voicemail: 'pending',
  failed: 'failed',
  'in-progress': 'active',
}

const outcomeColor: Record<CallOutcome, string> = {
  completed: 'text-success',
  missed: 'text-destructive',
  voicemail: 'text-muted-foreground',
  failed: 'text-destructive',
  'in-progress': 'text-primary',
}

export function CallCard({
  contactName,
  contactPhone,
  direction,
  outcome,
  duration,
  startedAt,
  agent,
  score,
  summary,
  className,
  onClick,
}: CallCardProps) {
  return (
    <Card
      className={cn(onClick && 'cursor-pointer hover:shadow-sm', className)}
      onClick={onClick}
    >
      <CardContent className="p-3 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className={cn('flex-shrink-0', outcomeColor[outcome])}>
              {outcomeIcon[outcome]}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{contactName}</p>
              {contactPhone && (
                <p className="text-[10px] text-muted-foreground">{contactPhone}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge
              variant={outcomeBadge[outcome] as Parameters<typeof Badge>[0]['variant']}
              className="text-[10px]"
            >
              {outcome}
            </Badge>
            <Badge variant="secondary" className="text-[10px]">
              {direction}
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
          {duration && (
            <span className="flex items-center gap-0.5">
              <Clock className="h-3 w-3" />
              {duration}
            </span>
          )}
          {startedAt && <span>{startedAt}</span>}
          {agent && <span>Agent: {agent}</span>}
          {score !== undefined && (
            <span className="ml-auto font-medium text-foreground">
              Score: {score}/100
            </span>
          )}
        </div>

        {summary && (
          <p className="text-xs text-muted-foreground line-clamp-2">{summary}</p>
        )}
      </CardContent>
    </Card>
  )
}
