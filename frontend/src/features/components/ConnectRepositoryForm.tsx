import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useConnectRepositoryMutation } from '../hooks/use-mutation'

interface ConnectRepositoryFormProps {
  onConnected: (scanId: string) => void
}

export function ConnectRepositoryForm({ onConnected }: ConnectRepositoryFormProps) {
  const [url, setUrl] = useState('')
  const mutation = useConnectRepositoryMutation(onConnected)

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault()
        mutation.mutate(url)
      }}
    >
      <div className="flex flex-col gap-2">
        <label htmlFor="repo-url" className="text-sm text-[#94A3B8]">
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
      {mutation.isError && (
        <p className="text-sm text-[#EF4444]">
          Failed to connect repository: {(mutation.error as Error).message}
        </p>
      )}
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? 'Connecting…' : 'Scan repository'}
      </Button>
    </form>
  )
}
