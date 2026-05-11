import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Lightbulb, TrendingUp, AlertTriangle, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'

export type InsightType = 'opportunity' | 'risk' | 'recommendation' | 'anomaly'

export interface InsightCardProps {
  title: string
  body: string
  type?: InsightType
  confidence?: number
  impact?: 'low' | 'medium' | 'high'
  source?: string
  generatedAt?: string
  actionLabel?: string
  onAction?: () => void
  className?: string
}

const typeConfig: Record<
  InsightType,
  { icon: React.ReactNode; color: string; badge: string }
> = {
  opportunity: {
    icon: <TrendingUp className="h-3.5 w-3.5" />,
    color: 'text-success',
    badge: 'active',
  },
  risk: {
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    color: 'text-warning',
    badge: 'escalated',
  },
  recommendation: {
    icon: <Lightbulb className="h-3.5 w-3.5" />,
    color: 'text-info',
    badge: 'info',
  },
  anomaly: {
    icon: <Zap className="h-3.5 w-3.5" />,
    color: 'text-destructive',
    badge: 'failed',
  },
}

const impactColor = {
  low: 'text-muted-foreground',
  medium: 'text-warning',
  high: 'text-destructive',
}

export function InsightCard({
  title,
  body,
  type = 'recommendation',
  confidence,
  impact,
  source,
  generatedAt,
  actionLabel,
  onAction,
  className,
}: InsightCardProps) {
  const config = typeConfig[type]

  return (
    <Card className={className}>
      <CardContent className="p-4 space-y-2">
        <div className="flex items-start gap-2">
          <span className={cn('mt-0.5 flex-shrink-0', config.color)}>
            {config.icon}
          </span>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium leading-none">{title}</p>
              <Badge
                variant={config.badge as Parameters<typeof Badge>[0]['variant']}
                className="flex-shrink-0 text-[10px]"
              >
                {type}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">{body}</p>
          </div>
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            {confidence !== undefined && (
              <span>Confidence: {confidence}%</span>
            )}
            {impact && (
              <span className={impactColor[impact]}>
                {impact.charAt(0).toUpperCase() + impact.slice(1)} impact
              </span>
            )}
            {source && <span>{source}</span>}
            {generatedAt && <span>{generatedAt}</span>}
          </div>

          {actionLabel && onAction && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onAction}
              className="h-6 px-2 text-xs"
            >
              {actionLabel}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
