import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { getErrorMessage } from '@/lib/errors'
import { useDisconnectRepositoryMutation } from '../api/disconnect-repository'
import type { Repository } from '../types/repository'

interface DisconnectRepositoryDialogProps {
  repository: Repository | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDisconnected: () => void
}

export function DisconnectRepositoryDialog({
  repository,
  open,
  onOpenChange,
  onDisconnected,
}: DisconnectRepositoryDialogProps) {
  const disconnectRepository = useDisconnectRepositoryMutation()
  const isPending = disconnectRepository.isPending

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) disconnectRepository.reset()
    onOpenChange(nextOpen)
  }

  const handleConfirm = () => {
    if (!repository) return
    disconnectRepository.mutate(repository.id, {
      onSuccess: () => {
        onDisconnected()
        handleOpenChange(false)
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Disconnect repository</DialogTitle>
          <DialogDescription>
            This permanently deletes{' '}
            <span className="font-mono text-white">{repository?.name}</span> and all of its scans,
            findings, reports, and indexed content. This cannot be undone.
          </DialogDescription>
        </DialogHeader>
        {disconnectRepository.isError && (
          <p className="text-sm text-destructive">
            Failed to disconnect repository: {getErrorMessage(disconnectRepository.error)}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isPending}
            className="bg-none bg-destructive shadow-[0_0_20px_-5px_rgba(239,68,68,0.5)] hover:shadow-[0_0_30px_-5px_rgba(239,68,68,0.6)]"
          >
            {isPending ? 'Disconnecting…' : 'Disconnect'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
