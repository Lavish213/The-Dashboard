import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, AlertCircle, Info, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export type AlertSeverity = 'critical' | 'warning' | 'info' | 'success'

export interface AlertCardProps {
  title: string
  message: string
  severity?: AlertSeverity
  timestamp?: string
  source?: string
  /** Primary CTA */
  actionLabel?: string
  onAction?: () => void
  /** Dismiss handler */
  onDismiss?: () => void
  className?: string
}

const severityConfig: Record<
  AlertSeverity,
  { icon: React.ReactNode; cardVariant: 'alert' | 'warning' | 'info' | 'success'; badge: string }
> = {
  critical: {
    icon: <AlertCircle className="h-4 w-4" />,
    cardVariant: 'alert',
    badge: 'failed',
  },
  warning: {
    icon: <AlertTriangle className="h-4 w-4" />,
    cardVariant: 'warning',
    badge: 'escalated',
  },
  info: {
    icon: <Info className="h-4 w-4" />,
    cardVariant: 'info',
    badge: 'info',
  },
  success: {
    icon: <CheckCircle2 className="h-4 w-4" />,
    cardVariant: 'success',
    badge: 'active',
  },
}

export function AlertCard({
  title,
  message,
  severity = 'warning',
  timestamp,
  source,
  actionLabel,
  onAction,
  onDismiss,
  className,
}: AlertCardProps) {
  const config = severityConfig[severity]

  return (
    <Card variant={config.cardVariant} className={className}>
      <CardContent className="p-3">
        <div className="flex gap-3">
          <span
            className={cn(
              'mt-0.5 flex-shrink-0',
              severity === 'critical' && 'text-destructive',
              severity === 'warning' && 'text-warning',
              severity === 'info' && 'text-info',
              severity === 'success' && 'text-success'
            )}
          >
            {config.icon}
          </span>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium leading-none">{title}</p>
                <Badge variant={config.badge as Parameters<typeof Badge>[0]['variant']} className="h-4 text-[10px]">
                  {severity}
                </Badge>
              </div>
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="flex-shrink-0 text-muted-foreground hover:text-foreground"
                  aria-label="Dismiss alert"
                >
                  ×
                </button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{message}</p>
            {(source || timestamp) && (
              <p className="text-[10px] text-muted-foreground/70">
                {source && <span>{source}</span>}
                {source && timestamp && <span> · </span>}
                {timestamp && <span>{timestamp}</span>}
              </p>
            )}
            {actionLabel && onAction && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onAction}
                className="mt-1 h-6 px-2 text-xs"
              >
                {actionLabel}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
