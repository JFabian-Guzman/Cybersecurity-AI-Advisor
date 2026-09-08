export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export const SEVERITY_RANK: Record<Severity, number> = Object.fromEntries(
  SEVERITY_ORDER.map((severity, index) => [severity, index]),
) as Record<Severity, number>

export const SEVERITY_BADGE_VARIANT: Record<
  Severity,
  'destructive' | 'warning' | 'secondary' | 'outline'
> = {
  critical: 'destructive',
  high: 'destructive',
  medium: 'warning',
  low: 'outline',
  info: 'secondary',
}

export function severityLabel(severity: Severity): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1)
}

export interface Finding {
  id: string
  scan_id: string
  user_id: string
  rule_id: string
  severity: Severity
  category: string
  file_path: string
  line_number: number | null
  message: string
  remediation: string
  created_at: string
}

const CATEGORY_LABELS: Record<string, string> = {
  docker: 'Docker',
  kubernetes: 'Kubernetes',
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category
}
