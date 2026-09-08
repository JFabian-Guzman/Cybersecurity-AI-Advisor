import type { ReactNode } from 'react'
import type { Finding } from '../types/findings'

interface FindingItemProps {
  finding: Finding
  leading: ReactNode
}

export function FindingItem({ finding, leading }: FindingItemProps) {
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {leading}
        <span className="text-xs text-muted-foreground">{finding.rule_id}</span>
        {finding.line_number != null && (
          <span className="text-xs text-muted-foreground">Line {finding.line_number}</span>
        )}
      </div>
      <p className="text-sm">
        <span className="font-semibold">Error: </span>
        {finding.message}
      </p>
      <p className="text-sm">
        <span className="font-semibold">Fix: </span>
        {finding.remediation}
      </p>
    </li>
  )
}
