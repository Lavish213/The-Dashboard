import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default:    'bg-primary/15 text-primary border border-primary/20',
        secondary:  'bg-secondary text-secondary-foreground',
        outline:    'border border-border text-muted-foreground',
        // Status variants
        active:     'bg-success/15 text-success border border-success/25',
        pending:    'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20',
        failed:     'bg-destructive/15 text-destructive border border-destructive/25',
        paused:     'bg-muted text-muted-foreground',
        escalated:  'bg-warning/15 text-warning border border-warning/25',
        completed:  'bg-muted text-muted-foreground',
        info:       'bg-info/15 text-info border border-info/25',
        // Solid variants
        'solid-destructive': 'bg-destructive text-destructive-foreground',
        'solid-success':     'bg-success text-success-foreground',
        'solid-warning':     'bg-warning text-warning-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
