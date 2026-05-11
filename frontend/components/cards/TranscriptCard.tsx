import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { MessageSquare, User, Bot } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface TranscriptTurn {
  id: string
  speaker: 'agent' | 'lead' | 'system'
  text: string
  timestamp?: string
  /** Highlight this turn (e.g. key moment) */
  highlight?: boolean
}

export interface TranscriptCardProps {
  callId: string
  turns: TranscriptTurn[]
  /** Max visible turns before truncation */
  maxTurns?: number
  /** Summary extracted from transcript */
  summary?: string
  /** Sentiment label */
  sentiment?: 'positive' | 'neutral' | 'negative'
  duration?: string
  className?: string
  onExpand?: () => void
}

const sentimentBadge = {
  positive: 'active',
  neutral: 'secondary',
  negative: 'failed',
} as const

function TurnRow({ turn }: { turn: TranscriptTurn }) {
  const isAgent = turn.speaker === 'agent'
  const isSystem = turn.speaker === 'system'

  return (
    <div
      className={cn(
        'flex gap-2 py-1',
        turn.highlight && 'rounded bg-warning/5 px-1'
      )}
    >
      <span className="mt-0.5 flex-shrink-0">
        {isSystem ? (
          <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-muted text-[8px] text-muted-foreground">S</span>
        ) : isAgent ? (
          <Bot className="h-4 w-4 text-primary" />
        ) : (
          <User className="h-4 w-4 text-muted-foreground" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium capitalize text-foreground">
            {turn.speaker}
          </span>
          {turn.timestamp && (
            <span className="text-[10px] text-muted-foreground/60">{turn.timestamp}</span>
          )}
          {turn.highlight && (
            <Badge variant="escalated" className="h-3 text-[8px] px-1">key</Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground">{turn.text}</p>
      </div>
    </div>
  )
}

export function TranscriptCard({
  callId: _callId,
  turns,
  maxTurns = 5,
  summary,
  sentiment,
  duration,
  className,
  onExpand,
}: TranscriptCardProps) {
  const visible = turns.slice(0, maxTurns)
  const hasMore = turns.length > maxTurns

  return (
    <Card className={className}>
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
          <p className="text-sm font-medium">Transcript</p>
          {duration && (
            <span className="text-xs text-muted-foreground">{duration}</span>
          )}
        </div>
        {sentiment && (
          <Badge variant={sentimentBadge[sentiment]} className="text-[10px]">
            {sentiment}
          </Badge>
        )}
      </div>
      <CardContent className="p-3 space-y-2">
        {summary && (
          <div className="rounded bg-muted/50 px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-0.5">Summary</p>
            <p className="text-xs">{summary}</p>
          </div>
        )}
        <div className="space-y-0.5">
          {visible.map((turn) => (
            <TurnRow key={turn.id} turn={turn} />
          ))}
        </div>
        {hasMore && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onExpand}
            className="h-6 w-full text-xs text-muted-foreground"
          >
            +{turns.length - maxTurns} more turns
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
