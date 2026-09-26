import * as React from 'react'
import { CircleAlert, Clock } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { Loading } from '@/components/ui/loading'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FilterCombobox } from './FilterCombobox'
import { ScanAlert } from './ScanAlert'
import { ScanTimer } from './ScanTimer'
import { FindingsByFile } from './FindingsByFile'
import { FindingsBySeverity } from './FindingsBySeverity'
import { ReportSummary } from './ReportSummary'
import { SCAN_POLL_TIMEOUT_MS, ScanStuckError, useScanQuery } from '../api/get-scan'
import { useFindingsQuery } from '../api/get-findings'
import { useRetryScanMutation } from '../api/retry-scan'
import { FINDING_CATEGORIES, SEVERITY_ORDER, severityLabel, categoryLabel } from '../types/findings'
import type { Severity } from '../types/findings'
import { getErrorMessage } from '@/lib/errors'

interface ScanStatusProps {
  scanId: string
}

export function ScanStatus({ scanId }: ScanStatusProps) {
  const [attempt, setAttempt] = React.useState(0)
  const { data, isLoading, isError, error } = useScanQuery(scanId, attempt)
  const retryScan = useRetryScanMutation(scanId)

  const [selectedSeverities, setSelectedSeverities] = React.useState<Severity[]>([])
  const [selectedCategories, setSelectedCategories] = React.useState<string[]>([])

  const findingsQuery = useFindingsQuery(
    scanId,
    { severities: selectedSeverities, categories: selectedCategories },
    data?.status === 'succeeded',
  )

  const handleRetry = () => {
    retryScan.mutate(undefined, {
      onSuccess: () => setAttempt((current) => current + 1),
    })
  }

  if (isLoading) return <Loading label="Checking scan status…" />
  if (isError) {
    if (error instanceof ScanStuckError) {
      const timeoutMinutes = SCAN_POLL_TIMEOUT_MS / 60_000
      return (
        <ScanAlert
          icon={<Clock />}
          title="Scan is taking longer than expected"
          description={`The scan hasn't made progress in over ${timeoutMinutes} minute${timeoutMinutes === 1 ? '' : 's'} and may be stuck. You can retry it now, or keep this window open in case the worker catches up.`}
          onRetry={handleRetry}
          retryPending={retryScan.isPending}
        />
      )
    }
    return <p className="text-sm text-destructive">Failed to load scan: {getErrorMessage(error)}</p>
  }
  if (!data) return null

  if (data.status === 'queued' || data.status === 'running') {
    return (
      <div className="flex items-center gap-3">
        <Loading label={data.status === 'running' ? 'Scanning repository…' : 'Scan queued…'} />
        <ScanTimer startedAt={data.started_at} finishedAt={null} />
      </div>
    )
  }

  if (data.status === 'failed') {
    const errorText = data.error ?? 'Unknown error'
    return (
      <div className="flex flex-col gap-2">
        <ScanTimer startedAt={data.started_at} finishedAt={data.finished_at} />
        <ScanAlert
          variant="destructive"
          icon={<CircleAlert />}
          title="Scan failed"
          description={errorText}
          errorText={errorText}
          onRetry={handleRetry}
          retryPending={retryScan.isPending}
        />
      </div>
    )
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
      <ScanTimer startedAt={data.started_at} finishedAt={data.finished_at} />
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
            <FilterCombobox
              items={SEVERITY_ORDER}
              value={selectedSeverities}
              onValueChange={setSelectedSeverities}
              label={severityLabel}
              placeholder="Filter by severity…"
              emptyText="No severities found."
            />

            <FilterCombobox
              items={FINDING_CATEGORIES}
              value={selectedCategories}
              onValueChange={setSelectedCategories}
              label={categoryLabel}
              placeholder="Filter by category…"
              emptyText="No categories found."
            />
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
