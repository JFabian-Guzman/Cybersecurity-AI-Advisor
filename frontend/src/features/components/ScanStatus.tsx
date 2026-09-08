import { Loading } from '@/components/ui/loading'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FindingsByFile } from './FindingsByFile'
import { FindingsBySeverity } from './FindingsBySeverity'
import { ReportSummary } from './ReportSummary'
import { useScanQuery } from '../api/get-scan'
import { getErrorMessage } from '@/lib/errors'

interface ScanStatusProps {
  scanId: string
}

export function ScanStatus({ scanId }: ScanStatusProps) {
  const { data, isLoading, isError, error } = useScanQuery(scanId)

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

  return (
    <div className="flex flex-col gap-4">
      <ReportSummary scanId={scanId} />
      <Tabs defaultValue="file">
        <TabsList variant="line">
          <TabsTrigger variant="line" value="file">
            By file
          </TabsTrigger>
          <TabsTrigger variant="line" value="severity">
            By severity
          </TabsTrigger>
        </TabsList>
        <TabsContent value="file">
          <FindingsByFile scanId={scanId} />
        </TabsContent>
        <TabsContent value="severity">
          <FindingsBySeverity scanId={scanId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
