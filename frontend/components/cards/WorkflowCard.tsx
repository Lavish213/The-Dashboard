import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { CheckCircle2, Circle, Clock, XCircle, PlayCircle } from 'lucide-react'

export type WorkflowStatus = 'idle' | 'running' | 'paused' | 'completed' | 'failed'

export interface WorkflowStep {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
}

export interface WorkflowCardProps {
  id: string
  name: string
  description?: string
  status: WorkflowStatus
  steps?: WorkflowStep[]
  progress?: number
  startedAt?: string
  completedAt?: string
  triggeredBy?: string
  runCount?: number
  className?: string
  onClick?: () => void
}

const workflowStatusBadge: Record<WorkflowStatus, string> = {
  idle: 'secondary',
  running: 'active',
  paused: 'pending',
  completed: 'completed',
  failed: 'failed',
}

const stepIcon: Record<WorkflowStep['status'], React.ReactNode> = {
  pending: <Circle className="h-3 w-3 text-muted-foreground/40" />,
  running: <PlayCircle className="h-3 w-3 text-primary animate-pulse" />,
  completed: <CheckCircle2 className="h-3 w-3 text-success" />,
  failed: <XCircle className="h-3 w-3 text-destructive" />,
  skipped: <Circle className="h-3 w-3 text-muted-foreground/20" />,
}

export function WorkflowCard({
  name,
  description,
  status,
  steps,
  progress,
  startedAt,
  completedAt,
  triggeredBy,
  runCount,
  className,
  onClick,
}: WorkflowCardProps) {
  const completedSteps = steps?.filter((s) => s.status === 'completed').length ?? 0
  const totalSteps = steps?.length ?? 0
  const computedProgress =
    progress !== undefined
      ? progress
      : totalSteps > 0
      ? Math.round((completedSteps / totalSteps) * 100)
      : undefined

  return (
    <Card
      className={cn(onClick && 'cursor-pointer hover:shadow-sm transition-shadow', className)}
      onClick={onClick}
    >
      <CardContent className="p-3 space-y-2.5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 space-y-0.5">
            <p className="text-sm font-medium truncate">{name}</p>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          <Badge
            variant={workflowStatusBadge[status] as Parameters<typeof Badge>[0]['variant']}
            className="flex-shrink-0 text-[10px]"
          >
            {status}
          </Badge>
        </div>

        {/* Steps */}
        {steps && steps.length > 0 && (
          <div className="space-y-1">
            {steps.map((step) => (
              <div key={step.id} className="flex items-center gap-2">
                <span className="flex-shrink-0">{stepIcon[step.status]}</span>
                <span
                  className={cn(
                    'text-xs truncate',
                    step.status === 'completed' && 'text-muted-foreground line-through',
                    step.status === 'failed' && 'text-destructive',
                    step.status === 'running' && 'text-foreground font-medium',
                    (step.status === 'pending' || step.status === 'skipped') &&
                      'text-muted-foreground'
                  )}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Progress bar */}
        {computedProgress !== undefined && (
          <Progress
            value={computedProgress}
            size="sm"
            color={status === 'failed' ? 'destructive' : status === 'completed' ? 'success' : 'default'}
          />
        )}

        {/* Footer meta */}
        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          <div className="flex items-center gap-2">
            {triggeredBy && <span>By {triggeredBy}</span>}
            {runCount !== undefined && <span>{runCount} runs</span>}
          </div>
          <div className="flex items-center gap-1">
            {startedAt && (
              <span className="flex items-center gap-0.5">
                <Clock className="h-2.5 w-2.5" />
                {startedAt}
              </span>
            )}
            {completedAt && <span>→ {completedAt}</span>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
