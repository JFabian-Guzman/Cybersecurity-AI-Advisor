import { Badge } from '@/components/ui/badge'
import { SEVERITY_BADGE_VARIANT, SEVERITY_ORDER, severityLabel } from '../types/findings'
import type { Finding, Severity } from '../types/findings'
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
  return (a.line_number ?? 0) - (b.line_number ?? 0)
}

interface FindingsBySeverityProps {
  findings: Finding[]
}

export function FindingsBySeverity({ findings }: FindingsBySeverityProps) {
  if (findings.length === 0) {
    return <p className="text-muted-foreground">No findings for this scan.</p>
  }

  const severityGroups = groupBySeverity(findings)

  const accordionGroups: FindingsAccordionGroup[] = SEVERITY_ORDER.filter(
    (severity) => (severityGroups.get(severity)?.length ?? 0) > 0,
  ).map((severity) => {
    const findingsForSeverity = severityGroups.get(severity) ?? []
    const sortedFindings = [...findingsForSeverity].sort(compareByFileThenLine)
    const count = findingsForSeverity.length

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
      findings: sortedFindings,
      itemLeading: (finding) => (
        <span className="font-mono text-xs text-muted-foreground">{finding.file_path}</span>
      ),
    }
  })

  return <FindingsAccordion groups={accordionGroups} />
}
