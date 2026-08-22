import { Loader2 } from 'lucide-react'
import { FindingsByFile } from './FindingsByFile'
import { ReportSummary } from './ReportSummary'
import { useScanQuery } from '../api/get-scan'

interface ScanStatusProps {
  scanId: string
}

function LoadingStatus({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-2 text-sm text-[#94A3B8]">
      <Loader2 className="size-4 animate-spin" />
      {label}
    </p>
  )
}

export function ScanStatus({ scanId }: ScanStatusProps) {
  const { data, isLoading, isError, error } = useScanQuery(scanId)

  if (isLoading) return <LoadingStatus label="Checking scan status…" />
  if (isError)
    return <p className="text-sm text-[#EF4444]">Failed to load scan: {(error as Error).message}</p>
  if (!data) return null

  if (data.status === 'queued' || data.status === 'running') {
    return (
      <LoadingStatus label={data.status === 'queued' ? 'Scan queued…' : 'Scanning repository…'} />
    )
  }

  if (data.status === 'failed') {
    return <p className="text-sm text-[#EF4444]">Scan failed: {data.error ?? 'Unknown error'}</p>
  }

  return (
    <div className="flex flex-col gap-4">
      <ReportSummary scanId={scanId} />
      <FindingsByFile scanId={scanId} />
    </div>
  )
}
