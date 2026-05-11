import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const containerVariants = cva('mx-auto w-full', {
  variants: {
    size: {
      sm:   'max-w-3xl',
      md:   'max-w-5xl',
      lg:   'max-w-7xl',
      full: 'max-w-none',
    },
    padding: {
      none: '',
      sm:   'px-4',
      md:   'px-6',
      lg:   'px-8',
    },
  },
  defaultVariants: {
    size: 'lg',
    padding: 'md',
  },
})

export interface ContainerProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof containerVariants> {}

export function Container({ className, size, padding, ...props }: ContainerProps) {
  return (
    <div className={cn(containerVariants({ size, padding }), className)} {...props} />
  )
}

/** Full-height page wrapper with background */
export function PageWrapper({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex min-h-screen flex-col bg-background text-foreground', className)}
      {...props}
    />
  )
}

/** Section with consistent vertical padding */
export function Section({
  className,
  tight,
  ...props
}: React.HTMLAttributes<HTMLElement> & { tight?: boolean }) {
  return (
    <section
      className={cn(tight ? 'py-4' : 'py-8', className)}
      {...props}
    />
  )
}
