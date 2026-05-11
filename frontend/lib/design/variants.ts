/**
 * Shared CVA variant patterns for Karpathys operational components
 */
import { cva } from 'class-variance-authority'

/** Status badge variants — used across badges, pills, row indicators */
export const statusBadgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default:    'bg-secondary text-secondary-foreground',
        active:     'bg-success/15 text-success border border-success/20',
        pending:    'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20',
        failed:     'bg-destructive/15 text-destructive border border-destructive/20',
        paused:     'bg-muted text-muted-foreground',
        escalated:  'bg-warning/15 text-warning border border-warning/20',
        completed:  'bg-muted text-muted-foreground',
        cancelled:  'bg-muted text-muted-foreground line-through',
        info:       'bg-info/15 text-info border border-info/20',
        outline:    'border border-border text-muted-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

/** Risk badge variants */
export const riskBadgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 text-xs font-semibold uppercase tracking-wide',
  {
    variants: {
      level: {
        critical: 'bg-destructive text-destructive-foreground',
        high:     'bg-warning/20 text-warning',
        medium:   'bg-yellow-500/20 text-yellow-400',
        low:      'bg-success/20 text-success',
      },
    },
    defaultVariants: {
      level: 'low',
    },
  }
)

/** Focus ring — canonical focus state for all interactive elements */
export const focusRingClass =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background'

/** Disabled state */
export const disabledClass = 'disabled:pointer-events-none disabled:opacity-50'

/** Interactive row variants */
export const interactiveRowVariants = cva(
  'flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-colors',
  {
    variants: {
      active: {
        true:  'bg-accent text-accent-foreground',
        false: 'text-foreground hover:bg-accent/60',
      },
    },
    defaultVariants: {
      active: false,
    },
  }
)

/** Card variants */
export const cardVariants = cva(
  'rounded-lg border bg-card text-card-foreground transition-colors',
  {
    variants: {
      variant: {
        default:  'border-border',
        elevated: 'border-border shadow-sm',
        outline:  'border-border bg-transparent',
        ghost:    'border-transparent',
        alert:    'border-destructive/50 bg-destructive/5',
        warning:  'border-warning/50 bg-warning/5',
        success:  'border-success/50 bg-success/5',
      },
      interactive: {
        true:  'cursor-pointer hover:border-border/80 hover:shadow-sm',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      interactive: false,
    },
  }
)

/** Skeleton variants */
export const skeletonVariants = cva(
  'animate-pulse rounded bg-muted',
  {
    variants: {
      variant: {
        default: '',
        shimmer: 'animate-shimmer bg-gradient-to-r from-muted via-muted/50 to-muted',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)
