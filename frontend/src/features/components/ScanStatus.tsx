import { FindingsByFile } from './FindingsByFile'
import { useScanQuery } from '../api/get-scan'

interface ScanStatusProps {
  scanId: string
}

export function ScanStatus({ scanId }: ScanStatusProps) {
  
  const { data, isLoading, isError, error } = useScanQuery(scanId)

  if (isLoading) return <p className="text-sm text-[#94A3B8]">Checking scan status…</p>
  if (isError)
    return <p className="text-sm text-[#EF4444]">Failed to load scan: {(error as Error).message}</p>
  if (!data) return null

  if (data.status === 'queued' || data.status === 'running') {
    return (
      <p className="text-sm text-[#94A3B8]">
        {data.status === 'queued' ? 'Scan queued…' : 'Scanning repository…'}
      </p>
    )
  }

  if (data.status === 'failed') {
    return <p className="text-sm text-[#EF4444]">Scan failed: {data.error ?? 'Unknown error'}</p>
  }

  return <FindingsByFile scanId={scanId} />
}
