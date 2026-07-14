import { useMutation } from '@tanstack/react-query'
import { connectRepository } from '../api/connect-repository'
import { deriveRepoName } from '@/lib/utils'

export function useConnectRepositoryMutation(onConnected: (scanId: string) => void) {
  return useMutation({
    mutationFn: (url: string) => connectRepository(url, deriveRepoName(url)),
    onSuccess: (data) => onConnected(data.scan_id),
  })
}
