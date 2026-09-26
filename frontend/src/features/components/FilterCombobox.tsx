import {
  Combobox,
  ComboboxChip,
  ComboboxChips,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxItem,
  ComboboxList,
  ComboboxValue,
  useComboboxAnchor,
} from '@/components/ui/combobox'

interface FilterComboboxProps<T extends string> {
  items: T[]
  value: T[]
  onValueChange: (value: T[]) => void
  label: (value: T) => string
  placeholder: string
  emptyText: string
}

export function FilterCombobox<T extends string>({
  items,
  value,
  onValueChange,
  label,
  placeholder,
  emptyText,
}: FilterComboboxProps<T>) {
  const anchor = useComboboxAnchor()

  return (
    <Combobox multiple autoHighlight items={items} value={value} onValueChange={onValueChange}>
      <ComboboxChips ref={anchor} className="w-full max-w-xs">
        <ComboboxValue>
          {(values) => (
            <>
              {values.map((value: T) => (
                <ComboboxChip key={value}>{label(value)}</ComboboxChip>
              ))}
              <ComboboxChipsInput placeholder={values.length === 0 ? placeholder : undefined} />
            </>
          )}
        </ComboboxValue>
      </ComboboxChips>
      <ComboboxContent anchor={anchor}>
        <ComboboxEmpty>{emptyText}</ComboboxEmpty>
        <ComboboxList>
          {(item) => (
            <ComboboxItem key={item} value={item}>
              {label(item)}
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  )
}
