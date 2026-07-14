export type Severity = 'high' | 'medium' | 'low'

export interface Finding {
  id: string
  scan_id: string
  user_id: string
  rule_id: string
  severity: Severity
  file_path: string
  line_number: number | null
  message: string
  remediation: string
  created_at: string
}
