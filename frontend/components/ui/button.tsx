import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium',
    'ring-offset-background transition-colors',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-50',
    '[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  ].join(' '),
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80',
        destructive:
          'bg-destructive text-destructive-foreground hover:bg-destructive/90 active:bg-destructive/80',
        outline:
          'border border-input bg-background hover:bg-accent hover:text-accent-foreground active:bg-accent/80',
        secondary:
          'bg-secondary text-secondary-foreground hover:bg-secondary/80 active:bg-secondary/70',
        ghost:
          'hover:bg-accent hover:text-accent-foreground active:bg-accent/80',
        link:
          'text-primary underline-offset-4 hover:underline',
        // Operational variants
        success:
          'bg-success/20 text-success border border-success/30 hover:bg-success/30',
        warning:
          'bg-warning/20 text-warning border border-warning/30 hover:bg-warning/30',
      },
      size: {
        default: 'h-8 px-3 py-1.5 text-sm',
        sm:      'h-7 rounded px-2.5 text-xs',
        lg:      'h-10 px-4 text-sm',
        xl:      'h-11 px-6 text-base',
        icon:    'h-8 w-8 p-0',
        'icon-sm': 'h-7 w-7 p-0',
        'icon-lg': 'h-10 w-10 p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }
