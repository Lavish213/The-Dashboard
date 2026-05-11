import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Show error ring state */
  error?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-8 w-full rounded-md border bg-background px-3 py-1.5 text-sm',
          'placeholder:text-muted-foreground',
          'ring-offset-background',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'transition-colors',
          error
            ? 'border-destructive focus-visible:ring-destructive'
            : 'border-input hover:border-ring/50',
          className
        )}
        ref={ref}
        aria-invalid={error ? 'true' : undefined}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'

export { Input }
