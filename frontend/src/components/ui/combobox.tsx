import * as React from 'react'
import { Combobox as ComboboxPrimitive } from '@base-ui/react'
import { CheckIcon, XIcon } from 'lucide-react'

import { cn } from '@/lib/utils'

const Combobox = ComboboxPrimitive.Root

function ComboboxValue(props: React.ComponentProps<typeof ComboboxPrimitive.Value>) {
  return <ComboboxPrimitive.Value data-slot="combobox-value" {...props} />
}

function ComboboxChips({
  className,
  ...props
}: React.ComponentPropsWithRef<typeof ComboboxPrimitive.Chips> & ComboboxPrimitive.Chips.Props) {
  return (
    <ComboboxPrimitive.Chips
      data-slot="combobox-chips"
      className={cn(
        'flex min-h-11 flex-1 flex-wrap items-center gap-1 rounded-lg border-b-2 border-white/20 bg-black/50 px-4 py-2 transition-[border-color,box-shadow] duration-200 focus-within:border-[#F7931A] focus-within:shadow-[0_10px_20px_-10px_rgba(247,147,26,0.3)]',
        className,
      )}
      {...props}
    />
  )
}

function ComboboxChip({
  className,
  children,
  showRemove = true,
  ...props
}: ComboboxPrimitive.Chip.Props & { showRemove?: boolean }) {
  return (
    <ComboboxPrimitive.Chip
      data-slot="combobox-chip"
      className={cn(
        'inline-flex items-center gap-1 rounded-full border border-[#F7931A]/30 bg-[#F7931A]/15 px-2.5 py-0.5 font-mono text-xs text-[#F7931A] has-disabled:pointer-events-none has-disabled:cursor-not-allowed has-disabled:opacity-50',
        className,
      )}
      {...props}
    >
      {children}
      {showRemove && (
        <ComboboxPrimitive.ChipRemove
          data-slot="combobox-chip-remove"
          className="ml-0.5 rounded-full p-0.5 text-[#F7931A]/60 transition-colors hover:bg-[#F7931A]/20 hover:text-[#F7931A]"
        >
          <XIcon className="size-3" />
        </ComboboxPrimitive.ChipRemove>
      )}
    </ComboboxPrimitive.Chip>
  )
}

function ComboboxChipsInput({ className, placeholder, ...props }: ComboboxPrimitive.Input.Props) {
  return (
    <ComboboxPrimitive.Input
      data-slot="combobox-chip-input"
      placeholder={placeholder}
      className={cn(
        'min-w-24 flex-1 bg-transparent font-mono text-sm text-white outline-none placeholder:text-white/30',
        className,
      )}
      {...props}
    />
  )
}

function ComboboxContent({
  className,
  children,
  side = 'bottom',
  sideOffset = 6,
  align = 'start',
  ...props
}: ComboboxPrimitive.Popup.Props &
  Pick<
    ComboboxPrimitive.Positioner.Props,
    'side' | 'align' | 'sideOffset' | 'alignOffset' | 'anchor'
  >) {
  return (
    <ComboboxPrimitive.Portal>
      <ComboboxPrimitive.Positioner
        side={side}
        sideOffset={sideOffset}
        align={align}
        anchor={props.anchor}
        className="isolate z-50"
      >
        <ComboboxPrimitive.Popup
          data-slot="combobox-content"
          className={cn(
            'w-[var(--anchor-width)] min-w-[calc(var(--anchor-width)+1.75rem)] max-w-[var(--available-width)] origin-[var(--transform-origin)] overflow-hidden rounded-lg border border-white/10 bg-[#0f1115] shadow-[0_10px_40px_-10px_rgba(0,0,0,0.6)]',
            className,
          )}
        >
          {children}
        </ComboboxPrimitive.Popup>
      </ComboboxPrimitive.Positioner>
    </ComboboxPrimitive.Portal>
  )
}

function ComboboxList({ className, ...props }: ComboboxPrimitive.List.Props) {
  return (
    <ComboboxPrimitive.List
      data-slot="combobox-list"
      className={cn('max-h-60 overflow-y-auto overscroll-contain p-1', className)}
      {...props}
    />
  )
}

function ComboboxItem({ className, children, ...props }: ComboboxPrimitive.Item.Props) {
  return (
    <ComboboxPrimitive.Item
      data-slot="combobox-item"
      className={cn(
        'relative flex w-full cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm text-white outline-none select-none data-highlighted:bg-[#F7931A]/10 data-highlighted:text-[#F7931A] data-disabled:pointer-events-none data-disabled:opacity-50',
        className,
      )}
      {...props}
    >
      {children}
      <ComboboxPrimitive.ItemIndicator className="ml-auto">
        <CheckIcon className="size-4 text-[#F7931A]" />
      </ComboboxPrimitive.ItemIndicator>
    </ComboboxPrimitive.Item>
  )
}

function ComboboxEmpty({ className, ...props }: ComboboxPrimitive.Empty.Props) {
  return (
    <ComboboxPrimitive.Empty
      data-slot="combobox-empty"
      className={cn('px-3 py-2 text-sm text-[#94A3B8]', className)}
      {...props}
    />
  )
}

function useComboboxAnchor() {
  return React.useRef<HTMLDivElement | null>(null)
}

export {
  Combobox,
  ComboboxValue,
  ComboboxChips,
  ComboboxChip,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxList,
  ComboboxItem,
  ComboboxEmpty,
  useComboboxAnchor,
}
