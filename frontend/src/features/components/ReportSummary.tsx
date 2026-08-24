import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useReportQuery } from '../api/get-report'
import { categoryLabel } from '../types/findings'
import { getErrorMessage } from '@/lib/errors'

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'] as const

const SEVERITY_BADGE_VARIANT: Record<string, 'destructive' | 'warning' | 'secondary' | 'outline'> =
  {
    critical: 'destructive',
    high: 'destructive',
    medium: 'warning',
    low: 'outline',
    info: 'secondary',
  }

interface ReportSummaryProps {
  scanId: string
}

export function ReportSummary({ scanId }: ReportSummaryProps) {
  const { data, isLoading, isError, error } = useReportQuery(scanId)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }

  if (isError) {
    return <p className="text-destructive">Failed to load report: {getErrorMessage(error)}</p>
  }

  if (!data) return null

  const severityEntries = SEVERITY_ORDER.filter((sev) => (data.severity_counts[sev] ?? 0) > 0).map(
    (sev) => [sev, data.severity_counts[sev]] as const,
  )
  const categoryEntries = Object.entries(data.category_counts)
  const ruleEntries = Object.entries(data.rule_counts)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scan Summary</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          {data.total_findings === 0
            ? 'No issues found.'
            : `${data.total_findings} ${data.total_findings === 1 ? 'finding' : 'findings'} total`}
        </p>

        {severityEntries.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Severity</span>
            <div className="flex flex-wrap gap-2">
              {severityEntries.map(([sev, count]) => (
                <Badge key={sev} variant={SEVERITY_BADGE_VARIANT[sev]}>
                  {sev}: {count}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {categoryEntries.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Category</span>
            <div className="flex flex-wrap gap-2">
              {categoryEntries.map(([cat, count]) => (
                <Badge key={cat} variant="secondary">
                  {categoryLabel(cat)}: {count}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {ruleEntries.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Rules</span>
            <div className="flex flex-wrap gap-2">
              {ruleEntries.map(([rule, count]) => (
                <Badge key={rule} variant="outline">
                  {rule}: {count}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
