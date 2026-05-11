import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const spinnerVariants = cva(
  'animate-spin rounded-full border-2 border-current border-t-transparent shrink-0',
  {
    variants: {
      size: {
        xs: 'h-3 w-3 border',
        sm: 'h-4 w-4',
        md: 'h-5 w-5',
        lg: 'h-6 w-6',
        xl: 'h-8 w-8 border-[3px]',
      },
      variant: {
        default:     'text-muted-foreground',
        primary:     'text-primary',
        destructive: 'text-destructive',
        success:     'text-success',
        white:       'text-white',
      },
    },
    defaultVariants: {
      size: 'md',
      variant: 'default',
    },
  }
)

export interface SpinnerProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof spinnerVariants> {
  label?: string
}

function Spinner({ className, size, variant, label = 'Loading…', ...props }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={cn('inline-flex items-center justify-center', className)}
      {...props}
    >
      <span className={cn(spinnerVariants({ size, variant }))} aria-hidden="true" />
    </span>
  )
}

/** Full-page / section loading overlay */
function LoadingOverlay({ label = 'Loading…' }: { label?: string }) {
  return (
    <div
      className="absolute inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm"
      role="status"
      aria-label={label}
    >
      <Spinner size="lg" variant="primary" />
    </div>
  )
}

export { Spinner, LoadingOverlay }
