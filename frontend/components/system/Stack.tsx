import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const stackVariants = cva('flex', {
  variants: {
    direction: {
      row:    'flex-row',
      col:    'flex-col',
      'row-reverse': 'flex-row-reverse',
      'col-reverse': 'flex-col-reverse',
    },
    gap: {
      0:  'gap-0',
      1:  'gap-1',
      2:  'gap-2',
      3:  'gap-3',
      4:  'gap-4',
      5:  'gap-5',
      6:  'gap-6',
      8:  'gap-8',
      10: 'gap-10',
    },
    align: {
      start:    'items-start',
      center:   'items-center',
      end:      'items-end',
      stretch:  'items-stretch',
      baseline: 'items-baseline',
    },
    justify: {
      start:    'justify-start',
      center:   'justify-center',
      end:      'justify-end',
      between:  'justify-between',
      around:   'justify-around',
      evenly:   'justify-evenly',
    },
    wrap: {
      nowrap: 'flex-nowrap',
      wrap:   'flex-wrap',
    },
  },
  defaultVariants: {
    direction: 'col',
    gap: 3,
    align: 'stretch',
  },
})

export interface StackProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof stackVariants> {}

export function Stack({ className, direction, gap, align, justify, wrap, ...props }: StackProps) {
  return (
    <div
      className={cn(stackVariants({ direction, gap, align, justify, wrap }), className)}
      {...props}
    />
  )
}

/** Horizontal flex row shorthand */
export function HStack({
  className,
  gap = 3,
  align = 'center',
  ...props
}: Omit<StackProps, 'direction'>) {
  return (
    <Stack
      direction="row"
      gap={gap}
      align={align}
      className={className}
      {...props}
    />
  )
}

/** Vertical flex column shorthand */
export function VStack({ className, gap = 3, ...props }: Omit<StackProps, 'direction'>) {
  return <Stack direction="col" gap={gap} className={className} {...props} />
}

/** Spacer — fills available flex space */
export function Spacer({ className }: { className?: string }) {
  return <div className={cn('flex-1', className)} aria-hidden="true" />
}
