import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useConnectRepositoryMutation } from '../api/connect-repository'
import { useCreateScanMutation } from '../api/create-scan'
import { getErrorMessage } from '@/lib/errors'

interface ConnectRepositoryFormProps {
  onConnected: (scanId: string, repositoryName: string) => void
}

export function ConnectRepositoryForm({ onConnected }: ConnectRepositoryFormProps) {
  const [url, setUrl] = useState('')
  const connectRepository = useConnectRepositoryMutation()
  const createScan = useCreateScanMutation()

  const isPending = connectRepository.isPending || createScan.isPending
  const isError = connectRepository.isError || createScan.isError
  const error = connectRepository.error ?? createScan.error

  const handleSubmit = (url: string) => {
    connectRepository.mutate(url, {
      onSuccess: (repository) => {
        createScan.mutate(repository.id, {
          onSuccess: (scan) => onConnected(scan.id, repository.name),
        })
      },
    })
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault()
        handleSubmit(url)
      }}
    >
      <div className="flex flex-col gap-2">
        <label htmlFor="repo-url" className="text-sm text-muted-foreground">
          Repository URL
        </label>
        <Input
          id="repo-url"
          type="url"
          required
          placeholder="https://github.com/owner/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
      </div>
      {isError && (
        <p className="text-sm text-destructive">
          Failed to connect repository: {getErrorMessage(error)}
        </p>
      )}
      <Button type="submit" disabled={isPending}>
        {isPending ? 'Connecting…' : 'Scan repository'}
      </Button>
    </form>
  )
}
