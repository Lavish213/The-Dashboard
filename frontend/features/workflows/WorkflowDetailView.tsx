'use client'

import { PageContainer } from '@/components/workspace/PageContainer'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { WorkflowStatusBadge } from './WorkflowStatusBadge'
import {
  useWorkflow,
  useWorkflowEvents,
  usePauseWorkflow,
  useResumeWorkflow,
  useCancelWorkflow,
  useRecoverWorkflow,
} from './useWorkflow'

interface Props {
  workflowId: string
}

export function WorkflowDetailView({ workflowId }: Props) {
  const { data: workflow, isLoading, error } = useWorkflow(workflowId)
  const { data: events = [] } = useWorkflowEvents(workflowId)

  const pause = usePauseWorkflow()
  const resume = useResumeWorkflow()
  const cancel = useCancelWorkflow()
  const recover = useRecoverWorkflow()

  if (isLoading) {
    return (
      <PageContainer title="Workflow">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </PageContainer>
    )
  }

  if (error || !workflow) {
    return (
      <PageContainer title="Workflow">
        <p className="text-sm text-destructive">Workflow not found.</p>
      </PageContainer>
    )
  }

  const status = workflow.workflow_status
  const canPause = status === 'active'
  const canResume = status === 'paused'
  const canCancel = status === 'active' || status === 'paused'
  const canRecover = status === 'failed'

  return (
    <PageContainer
      title={`Workflow`}
      description={workflow.workflow_type.replace('_', ' ')}
      actions={
        <div className="flex gap-2">
          {canPause && (
            <Button
              size="sm"
              variant="outline"
              disabled={pause.isPending}
              onClick={() => pause.mutate(workflowId)}
            >
              Pause
            </Button>
          )}
          {canResume && (
            <Button
              size="sm"
              variant="outline"
              disabled={resume.isPending}
              onClick={() => resume.mutate(workflowId)}
            >
              Resume
            </Button>
          )}
          {canRecover && (
            <Button
              size="sm"
              variant="outline"
              disabled={recover.isPending}
              onClick={() => recover.mutate(workflowId)}
            >
              Recover
            </Button>
          )}
          {canCancel && (
            <Button
              size="sm"
              variant="destructive"
              disabled={cancel.isPending}
              onClick={() => cancel.mutate(workflowId)}
            >
              Cancel
            </Button>
          )}
        </div>
      }
    >
      <div className="space-y-4">
        {/* Status row */}
        <Card>
          <CardContent className="flex flex-wrap gap-6 pt-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Status</p>
              <WorkflowStatusBadge status={status} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Type</p>
              <span className="capitalize">{workflow.workflow_type.replace('_', ' ')}</span>
            </div>
            {workflow.current_step && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Current Step</p>
                <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{workflow.current_step}</code>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground mb-1">Correlation ID</p>
              <code className="text-xs text-muted-foreground">{workflow.correlation_id.slice(0, 8)}…</code>
            </div>
          </CardContent>
        </Card>

        {/* Event log */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Event Log</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <p className="text-xs text-muted-foreground">No events.</p>
            ) : (
              <ol className="space-y-1.5">
                {events.map((evt) => (
                  <li key={evt.id} className="flex items-start gap-3 text-xs">
                    <span className="text-muted-foreground shrink-0 w-40 truncate">
                      {new Date(evt.created_at).toLocaleTimeString()}
                    </span>
                    <Badge variant="outline" className="shrink-0 font-mono text-[10px] py-0">
                      {evt.event_type}
                    </Badge>
                    <span className="text-muted-foreground truncate">
                      {evt.actor_type}
                      {evt.actor_id ? ` · ${evt.actor_id.slice(0, 8)}` : ''}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}
