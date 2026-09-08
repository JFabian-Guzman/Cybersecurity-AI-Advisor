import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useFindingsQuery } from '../api/get-findings'
import { useReportQuery } from '../api/get-report'
import { SEVERITY_BADGE_VARIANT, SEVERITY_ORDER, severityLabel } from '../types/findings'
import type { Finding, Severity } from '../types/findings'
import { getErrorMessage } from '@/lib/errors'
import { FindingsAccordion } from './FindingsAccordion'
import type { FindingsAccordionGroup } from './FindingsAccordion'

function groupBySeverity(findings: Finding[]): Map<Severity, Finding[]> {
  const groups = new Map<Severity, Finding[]>()
  for (const finding of findings) {
    const existing = groups.get(finding.severity)
    if (existing) {
      existing.push(finding)
    } else {
      groups.set(finding.severity, [finding])
    }
  }
  return groups
}

function compareByFileThenLine(a: Finding, b: Finding): number {
  const byFile = a.file_path.localeCompare(b.file_path)
  if (byFile !== 0) return byFile
  // Findings with no line number sort before line 1 within the same file.
  return (a.line_number ?? 0) - (b.line_number ?? 0)
}

interface FindingsBySeverityProps {
  scanId: string
}

export function FindingsBySeverity({ scanId }: FindingsBySeverityProps) {
  const findingsQuery = useFindingsQuery(scanId)
  const reportQuery = useReportQuery(scanId)

  if (findingsQuery.isLoading || reportQuery.isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    )
  }

  if (findingsQuery.isError) {
    return (
      <p className="text-destructive">
        Failed to load findings: {getErrorMessage(findingsQuery.error)}
      </p>
    )
  }

  if (reportQuery.isError) {
    return (
      <p className="text-destructive">Failed to load report: {getErrorMessage(reportQuery.error)}</p>
    )
  }

  if (!findingsQuery.data || !reportQuery.data) return null

  if (findingsQuery.data.length === 0) {
    return <p className="text-muted-foreground">No findings for this scan.</p>
  }

  const severityCounts = reportQuery.data.severity_counts
  const severityGroups = groupBySeverity(findingsQuery.data)

  const accordionGroups: FindingsAccordionGroup[] = SEVERITY_ORDER.filter(
    (severity) => (severityCounts[severity] ?? 0) > 0,
  ).map((severity) => {
    const count = severityCounts[severity]
    const findings = [...(severityGroups.get(severity) ?? [])].sort(compareByFileThenLine)

    return {
      key: severity,
      trigger: (
        <span className="flex items-center gap-2">
          <span className="text-sm font-medium">{severityLabel(severity)}</span>
          <Badge variant={SEVERITY_BADGE_VARIANT[severity]}>
            {count} {count === 1 ? 'finding' : 'findings'}
          </Badge>
        </span>
      ),
      findings,
      itemLeading: (finding) => (
        <span className="font-mono text-xs text-muted-foreground">{finding.file_path}</span>
      ),
    }
  })

  return <FindingsAccordion groups={accordionGroups} />
}
