import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useFindingsQuery } from '../api/get-findings'
import { categoryLabel } from '../types/findings'
import type { Finding, Severity } from '../types/findings'

const SEVERITY_RANK: Record<Severity, number> = { high: 0, medium: 1, low: 2 }

const SEVERITY_BADGE_VARIANT: Record<Severity, 'destructive' | 'warning' | 'outline'> = {
  high: 'destructive',
  medium: 'warning',
  low: 'outline',
}

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
    'low',
  )
}

interface FindingsByFileProps {
  scanId: string
}

export function FindingsByFile({ scanId }: FindingsByFileProps) {
  const { data, isLoading, isError, error } = useFindingsQuery(scanId)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    )
  }

  if (isError) {
    return <p className="text-destructive">Failed to load findings: {(error as Error).message}</p>
  }

  if (!data || data.length === 0) {
    return <p className="text-muted-foreground">No findings for this scan.</p>
  }

  const categoryGroups = groupByCategory(data)

  return (
    <div className="flex flex-col gap-6">
      {[...categoryGroups.entries()].map(([category, categoryFindings]) => {
        const groups = groupByFile(categoryFindings)

        return (
          <div key={category} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{categoryLabel(category)}</Badge>
              <span className="text-xs text-muted-foreground">
                {categoryFindings.length} {categoryFindings.length === 1 ? 'finding' : 'findings'}
              </span>
            </div>
            <Accordion type="multiple" className="w-full">
              {[...groups.entries()].map(([filePath, findings]) => (
                <AccordionItem key={filePath} value={filePath}>
                  <AccordionTrigger>
                    <span className="flex items-center gap-2">
                      <span className="font-mono text-sm">{filePath}</span>
                      <Badge variant={SEVERITY_BADGE_VARIANT[worstSeverity(findings)]}>
                        {findings.length} {findings.length === 1 ? 'finding' : 'findings'}
                      </Badge>
                    </span>
                  </AccordionTrigger>
                  <AccordionContent>
                    <ul className="flex flex-col gap-3">
                      {findings.map((finding) => (
                        <li key={finding.id} className="flex flex-col gap-1">
                          <div className="flex items-center gap-2">
                            <Badge variant={SEVERITY_BADGE_VARIANT[finding.severity]}>
                              {finding.severity}
                            </Badge>
                            <span className="text-xs text-muted-foreground">{finding.rule_id}</span>
                            <span className="text-xs text-muted-foreground">
                              {finding.line_number && `Line  ${finding.line_number}`}
                            </span>
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
                      ))}
                    </ul>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        )
      })}
    </div>
  )
}
