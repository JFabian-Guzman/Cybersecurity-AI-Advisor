export interface ScanReport {
  scan_id: string
  total_findings: number
  severity_counts: Record<string, number>
  rule_counts: Record<string, number>
  category_counts: Record<string, number>
  created_at: string
}
