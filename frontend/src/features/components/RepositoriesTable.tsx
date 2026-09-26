import { Info, RotateCwIcon } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import type { Repository } from '../types/repository'

interface RepositoriesTableProps {
  repositories: Repository[]
  isPending: boolean
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
  onRetry: (repository: Repository) => void
  onViewDetails: (repository: Repository) => void
}

export function RepositoriesTable({
  repositories,
  isPending,
  total,
  page,
  pageSize,
  onPageChange,
  onRetry,
  onViewDetails,
}: RepositoriesTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">Repositories</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isPending ? (
            <TableRow>
              <TableCell colSpan={2} className="text-center">
                <Spinner className="mx-auto" />
              </TableCell>
            </TableRow>
          ) : repositories.length === 0 ? (
            <TableRow>
              <TableCell colSpan={2} className="text-center text-muted-foreground">
                No repositories connected yet
              </TableCell>
            </TableRow>
          ) : (
            repositories.map((repository) => {
              const isScanning =
                repository.last_scan_status === 'queued' ||
                repository.last_scan_status === 'running'

              return (
                <TableRow key={repository.id}>
                  <TableCell className="font-medium">{repository.name}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Retry scan"
                        title="Retry scan"
                        disabled={isScanning}
                        onClick={() => onRetry(repository)}
                      >
                        {isScanning ? (
                          <Spinner className="size-5" />
                        ) : (
                          <RotateCwIcon className="size-5" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="View scan details"
                        title="View scan details"
                        onClick={() => onViewDetails(repository)}
                      >
                        <Info className="size-5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              )
            })
          )}
        </TableBody>
      </Table>
      {!isPending && repositories.length > 0 && totalPages > 1 && (
        <Pagination className="mt-4">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                aria-disabled={page === 1}
                className={page === 1 ? 'pointer-events-none opacity-50' : undefined}
                onClick={(e) => {
                  e.preventDefault()
                  if (page > 1) onPageChange(page - 1)
                }}
              />
            </PaginationItem>
            {(() => {
              const start = Math.max(1, page - 2)
              const end = Math.min(totalPages, page + 2)
              const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i)
              return (
                <>
                  {start > 1 && (
                    <PaginationItem>
                      <PaginationEllipsis />
                    </PaginationItem>
                  )}
                  {pages.map((p) => (
                    <PaginationItem key={p}>
                      <PaginationLink
                        href="#"
                        isActive={p === page}
                        onClick={(e) => {
                          e.preventDefault()
                          onPageChange(p)
                        }}
                      >
                        {p}
                      </PaginationLink>
                    </PaginationItem>
                  ))}
                  {end < totalPages && (
                    <PaginationItem>
                      <PaginationEllipsis />
                    </PaginationItem>
                  )}
                </>
              )
            })()}
            <PaginationItem>
              <PaginationNext
                href="#"
                aria-disabled={page === totalPages}
                className={page === totalPages ? 'pointer-events-none opacity-50' : undefined}
                onClick={(e) => {
                  e.preventDefault()
                  if (page < totalPages) onPageChange(page + 1)
                }}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </>
  )
}
