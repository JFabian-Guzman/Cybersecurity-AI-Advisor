import { useMutation } from '@tanstack/react-query'
import { connectRepository } from '../api/connect-repository'
import { deriveRepoName } from '@/lib/utils'

export function useConnectRepositoryMutation() {
  return useMutation({
    mutationFn: async (url: string) => {
      const repository = await connectRepository(url, deriveRepoName(url))
      return repository
    },
  })
}
