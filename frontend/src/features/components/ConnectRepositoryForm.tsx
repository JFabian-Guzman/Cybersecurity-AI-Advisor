import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useConnectRepositoryMutation } from '../api/connect-repository'
import { useCreateScanMutation } from '../api/create-scan'
import { getErrorMessage } from '@/lib/errors'
import { RepositoriesTable } from './RepositoriesTable'
import { RepositoryScansModal } from './RepositoryScansModal'
import { DisconnectRepositoryDialog } from './DisconnectRepositoryDialog'
import { useRepositoryByUserQuery } from '../api/get-repositories-by-user'
import type { Repository } from '../types/repository'

interface ConnectRepositoryFormProps {
  onConnected: (scanId: string, repositoryName: string) => void
}

const PAGE_SIZE = 5

export function ConnectRepositoryForm({ onConnected }: ConnectRepositoryFormProps) {
  const [url, setUrl] = useState('')
  const connectRepository = useConnectRepositoryMutation()
  const createScan = useCreateScanMutation()

  const isPending = connectRepository.isPending || createScan.isPending
  const isError = connectRepository.isError || createScan.isError
  const error = connectRepository.error ?? createScan.error

  const startScan = (repositoryId: string, repositoryName: string) => {
    createScan.mutate(repositoryId, {
      onSuccess: (scan) => onConnected(scan.id, repositoryName),
    })
  }

  const handleSubmit = (url: string) => {
    connectRepository.mutate(url, {
      onSuccess: (repository) => startScan(repository.id, repository.name),
    })
  }

  const handleRetry = (repository: Repository) => {
    startScan(repository.id, repository.name)
  }

  const [selectedRepository, setSelectedRepository] = useState<Repository | null>(null)
  const [repositoryToDisconnect, setRepositoryToDisconnect] = useState<Repository | null>(null)

  const [page, setPage] = useState(1)

  const { data, isPending: isRepositoriesPending } = useRepositoryByUserQuery(
    '1',
    PAGE_SIZE,
    (page - 1) * PAGE_SIZE,
  )

  const handleDisconnected = () => {
    // Removing the only row on a later page would leave the user on an empty page.
    const isLastItemOnPage = (data?.items.length ?? 0) === 1
    if (isLastItemOnPage && page > 1) setPage(page - 1)
  }

  return (
    <>
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
      <div className="mb-5"></div>
      <RepositoriesTable
        repositories={data?.items ?? []}
        isPending={isRepositoriesPending}
        total={data?.total ?? 0}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={setPage}
        onRetry={handleRetry}
        onViewDetails={setSelectedRepository}
        onDisconnect={setRepositoryToDisconnect}
      />
      <RepositoryScansModal
        repository={selectedRepository}
        open={!!selectedRepository}
        onOpenChange={(open) => {
          if (!open) setSelectedRepository(null)
        }}
      />
      <DisconnectRepositoryDialog
        repository={repositoryToDisconnect}
        open={!!repositoryToDisconnect}
        onOpenChange={(open) => {
          if (!open) setRepositoryToDisconnect(null)
        }}
        onDisconnected={handleDisconnected}
      />
    </>
  )
}
