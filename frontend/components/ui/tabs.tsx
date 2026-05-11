'use client'

import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import { cn } from '@/lib/utils'

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List> & {
    variant?: 'default' | 'pills' | 'underline'
  }
>(({ className, variant = 'default', ...props }, ref) => {
  const variantClass = {
    default:   'inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground',
    pills:     'inline-flex items-center gap-1',
    underline: 'inline-flex items-center gap-1 border-b border-border',
  }[variant]

  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(variantClass, className)}
      {...props}
    />
  )
})
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger> & {
    variant?: 'default' | 'pills' | 'underline'
  }
>(({ className, variant = 'default', ...props }, ref) => {
  const variantClass = {
    default:
      'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm',
    pills:
      'inline-flex items-center justify-center whitespace-nowrap rounded-full px-3 py-1 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground',
    underline:
      'inline-flex items-center justify-center whitespace-nowrap border-b-2 border-transparent px-3 pb-2 pt-1 text-sm font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 data-[state=active]:border-primary data-[state=active]:text-foreground data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground',
  }[variant]

  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(variantClass, className)}
      {...props}
    />
  )
})
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
