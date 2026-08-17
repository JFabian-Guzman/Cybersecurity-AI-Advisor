import { useMutation } from '@tanstack/react-query'
import { connectRepository } from '../api/connect-repository'
import { createScan } from '../api/create-scan'
import { deriveRepoName } from '@/lib/utils'

export function useConnectRepositoryMutation(onConnected: (scanId: string) => void) {
  return useMutation({
    mutationFn: async (url: string) => {
      const repository = await connectRepository(url, deriveRepoName(url))
      return createScan(repository.id)
    },
    onSuccess: (scan) => onConnected(scan.id),
  })
}
