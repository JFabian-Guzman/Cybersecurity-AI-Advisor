import * as React from 'react'
import { Tabs as TabsPrimitive } from 'radix-ui'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

function Tabs({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      className={cn('flex flex-col gap-2', className)}
      {...props}
    />
  )
}

const tabsListVariants = cva('inline-flex h-9 w-fit items-center justify-center gap-1', {
  variants: {
    variant: {
      default: 'rounded-lg border border-white/10 bg-white/5 p-1',
      line: 'gap-4 border-b border-white/10',
    },
  },
  defaultVariants: { variant: 'default' },
})

function TabsList({
  className,
  variant,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List> & VariantProps<typeof tabsListVariants>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn(tabsListVariants({ variant }), className)}
      {...props}
    />
  )
}

const tabsTriggerVariants = cva(
  'inline-flex items-center justify-center gap-1.5 text-sm font-medium whitespace-nowrap text-muted-foreground outline-none transition-colors duration-200 hover:text-[#F7931A] focus-visible:ring-2 focus-visible:ring-[#F7931A]/50 cursor-pointer disabled:pointer-events-none disabled:opacity-50 disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        default:
          'flex-1 rounded-md px-3 py-1 data-[state=active]:bg-[#F7931A]/15 data-[state=active]:text-[#F7931A]',
        line: 'border-b-2 border-transparent px-1 pb-2 data-[state=active]:border-[#F7931A] data-[state=active]:text-[#F7931A]',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

function TabsTrigger({
  className,
  variant,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger> & VariantProps<typeof tabsTriggerVariants>) {
  return (
    <TabsPrimitive.Trigger
      data-slot="tabs-trigger"
      className={cn(tabsTriggerVariants({ variant }), className)}
      {...props}
    />
  )
}

function TabsContent({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-content"
      className={cn('flex-1 outline-none', className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
