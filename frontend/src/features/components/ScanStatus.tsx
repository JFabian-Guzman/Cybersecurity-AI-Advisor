import * as React from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Loading } from '@/components/ui/loading'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
import { FindingsByFile } from './FindingsByFile'
import { FindingsBySeverity } from './FindingsBySeverity'
import { ReportSummary } from './ReportSummary'
import { useScanQuery } from '../api/get-scan'
import { useFindingsQuery } from '../api/get-findings'
import { FINDING_CATEGORIES, SEVERITY_ORDER, severityLabel, categoryLabel } from '../types/findings'
import type { Severity } from '../types/findings'
import { getErrorMessage } from '@/lib/errors'

interface ScanStatusProps {
  scanId: string
}

export function ScanStatus({ scanId }: ScanStatusProps) {
  const { data, isLoading, isError, error } = useScanQuery(scanId)

  const [selectedSeverities, setSelectedSeverities] = React.useState<Severity[]>([])
  const [selectedCategories, setSelectedCategories] = React.useState<string[]>([])

  const severityAnchor = useComboboxAnchor()
  const categoryAnchor = useComboboxAnchor()

  const findingsQuery = useFindingsQuery(
    scanId,
    { severities: selectedSeverities, categories: selectedCategories },
    data?.status === 'succeeded',
  )

  if (isLoading) return <Loading label="Checking scan status…" />
  if (isError)
    return <p className="text-sm text-destructive">Failed to load scan: {getErrorMessage(error)}</p>
  if (!data) return null

  if (data.status === 'queued' || data.status === 'running') {
    return <Loading label={data.status === 'queued' ? 'Scan queued…' : 'Scanning repository…'} />
  }

  if (data.status === 'failed') {
    return <p className="text-sm text-destructive">Scan failed: {data.error ?? 'Unknown error'}</p>
  }

  if (findingsQuery.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    )
  }

  if (findingsQuery.isError) {
    return (
      <p className="text-sm text-destructive">
        Failed to load findings: {getErrorMessage(findingsQuery.error)}
      </p>
    )
  }

  const findings = findingsQuery.data ?? []

  return (
    <div className="flex flex-col gap-4">
      <ReportSummary scanId={scanId} />

      <Tabs defaultValue="file">
        <div className="mb-4 flex items-end">
          <TabsList variant="line" className="border-b-0">
            <TabsTrigger variant="line" value="file">
              By file
            </TabsTrigger>
            <TabsTrigger variant="line" value="severity">
              By severity
            </TabsTrigger>
          </TabsList>
          <div className="ml-auto flex flex-wrap gap-3">
            <Combobox
              multiple
              autoHighlight
              items={SEVERITY_ORDER}
              value={selectedSeverities}
              onValueChange={setSelectedSeverities}
            >
              <ComboboxChips ref={severityAnchor} className="w-full max-w-xs">
                <ComboboxValue>
                  {(values) => (
                    <>
                      {values.map((value: Severity) => (
                        <ComboboxChip key={value}>{severityLabel(value)}</ComboboxChip>
                      ))}
                      <ComboboxChipsInput
                        placeholder={values.length === 0 ? 'Filter by severity…' : undefined}
                      />
                    </>
                  )}
                </ComboboxValue>
              </ComboboxChips>
              <ComboboxContent anchor={severityAnchor}>
                <ComboboxEmpty>No severities found.</ComboboxEmpty>
                <ComboboxList>
                  {(item) => (
                    <ComboboxItem key={item} value={item}>
                      {severityLabel(item)}
                    </ComboboxItem>
                  )}
                </ComboboxList>
              </ComboboxContent>
            </Combobox>

            <Combobox
              multiple
              autoHighlight
              items={FINDING_CATEGORIES}
              value={selectedCategories}
              onValueChange={setSelectedCategories}
            >
              <ComboboxChips ref={categoryAnchor} className="w-full max-w-xs">
                <ComboboxValue>
                  {(values) => (
                    <>
                      {values.map((value: string) => (
                        <ComboboxChip key={value}>{categoryLabel(value)}</ComboboxChip>
                      ))}
                      <ComboboxChipsInput
                        placeholder={values.length === 0 ? 'Filter by category…' : undefined}
                      />
                    </>
                  )}
                </ComboboxValue>
              </ComboboxChips>
              <ComboboxContent anchor={categoryAnchor}>
                <ComboboxEmpty>No categories found.</ComboboxEmpty>
                <ComboboxList>
                  {(item) => (
                    <ComboboxItem key={item} value={item}>
                      {categoryLabel(item)}
                    </ComboboxItem>
                  )}
                </ComboboxList>
              </ComboboxContent>
            </Combobox>
          </div>
        </div>
        <TabsContent value="file">
          <FindingsByFile findings={findings} />
        </TabsContent>
        <TabsContent value="severity">
          <FindingsBySeverity findings={findings} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
