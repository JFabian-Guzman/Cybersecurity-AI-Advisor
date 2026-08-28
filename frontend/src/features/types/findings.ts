export type Severity = 'high' | 'medium' | 'low'

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
