import { Badge } from '@/components/ui/badge'
import { categoryLabel, SEVERITY_BADGE_VARIANT, SEVERITY_RANK } from '../types/findings'
import type { Finding, Severity } from '../types/findings'
import { FindingsAccordion } from './FindingsAccordion'
import type { FindingsAccordionGroup } from './FindingsAccordion'

function groupByFile(findings: Finding[]): Map<string, Finding[]> {
  const groups = new Map<string, Finding[]>()
  for (const finding of findings) {
    const existing = groups.get(finding.file_path)
    if (existing) {
      existing.push(finding)
    } else {
      groups.set(finding.file_path, [finding])
    }
  }
  return groups
}

function groupByCategory(findings: Finding[]): Map<string, Finding[]> {
  const groups = new Map<string, Finding[]>()
  for (const finding of findings) {
    const existing = groups.get(finding.category)
    if (existing) {
      existing.push(finding)
    } else {
      groups.set(finding.category, [finding])
    }
  }
  return groups
}

function worstSeverity(findings: Finding[]): Severity {
  return findings.reduce<Severity>(
    (worst, finding) =>
      SEVERITY_RANK[finding.severity] < SEVERITY_RANK[worst] ? finding.severity : worst,
    'info',
  )
}

interface FindingsByFileProps {
  findings: Finding[]
}

export function FindingsByFile({ findings }: FindingsByFileProps) {
  if (findings.length === 0) {
    return <p className="text-muted-foreground">No findings for this scan.</p>
  }

  const categoryGroups = groupByCategory(findings)

  return (
    <div className="flex flex-col gap-6">
      {[...categoryGroups.entries()].map(([category, categoryFindings]) => {
        const fileGroups = groupByFile(categoryFindings)

        const accordionGroups: FindingsAccordionGroup[] = [...fileGroups.entries()].map(
          ([filePath, findings]) => ({
            key: filePath,
            trigger: (
              <span className="flex items-center gap-2">
                <span className="font-mono text-sm">{filePath}</span>
                <Badge variant={SEVERITY_BADGE_VARIANT[worstSeverity(findings)]}>
                  {findings.length} {findings.length === 1 ? 'finding' : 'findings'}
                </Badge>
              </span>
            ),
            findings: [...findings].sort(
              (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity],
            ),
            itemLeading: (finding) => (
              <Badge variant={SEVERITY_BADGE_VARIANT[finding.severity]}>{finding.severity}</Badge>
            ),
          }),
        )

        return (
          <div key={category} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{categoryLabel(category)}</Badge>
              <span className="text-xs text-muted-foreground">
                {categoryFindings.length} {categoryFindings.length === 1 ? 'finding' : 'findings'}
              </span>
            </div>
            <FindingsAccordion groups={accordionGroups} />
          </div>
        )
      })}
    </div>
  )
}
