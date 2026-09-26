import * as React from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

interface ScanAlertProps {
  variant?: 'default' | 'destructive'
  icon: React.ReactNode
  title: string
  description: string
  onRetry?: () => void
  retryPending?: boolean
  errorText?: string
}

export function ScanAlert({
  variant = 'default',
  icon,
  title,
  description,
  onRetry,
  retryPending,
  errorText,
}: ScanAlertProps) {
  const showDetails = errorText !== undefined && errorText.length > 160

  return (
    <Alert variant={variant}>
      {icon}
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{description}</AlertDescription>
      {showDetails && (
        <details className="col-start-2 [&>summary]:cursor-pointer [&>summary]:select-none">
          <summary className="font-medium text-destructive/80 hover:text-destructive">
            Show full error
          </summary>
          <pre className="mt-2 max-h-48 overflow-auto rounded-md border border-destructive/20 bg-background/50 p-3 font-mono text-xs text-destructive/90 whitespace-pre-wrap">
            {errorText}
          </pre>
        </details>
      )}
      {onRetry && (
        <Button
          variant="default"
          size="sm"
          className="col-start-2 justify-self-start"
          onClick={onRetry}
          disabled={retryPending}
        >
          {retryPending ? 'Retrying…' : 'Retry scan'}
        </Button>
      )}
    </Alert>
  )
}
