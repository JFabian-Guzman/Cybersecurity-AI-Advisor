import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../lib/api-client'

export async function disconnectRepository(repositoryId: string): Promise<void> {
  await apiClient.delete(`/api/repositories/${repositoryId}`)
}

export function useDisconnectRepositoryMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: disconnectRepository,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
    },
  })
}
