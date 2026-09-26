import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
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
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { Info } from 'lucide-react'
import { useScansByRepositoryQuery } from '../api/get-scans-by-repository'
import type { Repository } from '../types/repository'
import type { ScanState } from '../types/scan'
import { formatDateTime } from '@/lib/format-date'

interface RepositoryScansModalProps {
  repository: Repository | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

const PAGE_SIZE = 5

const STATUS_BADGE_VARIANT: Record<ScanState, 'success' | 'destructive' | 'warning'> = {
  succeeded: 'success',
  failed: 'destructive',
  queued: 'warning',
  running: 'warning',
}

export function RepositoryScansModal({
  repository,
  open,
  onOpenChange,
}: RepositoryScansModalProps) {
  const [page, setPage] = useState(1)

  const { data, isPending } = useScansByRepositoryQuery(
    repository?.id ?? '',
    PAGE_SIZE,
    (page - 1) * PAGE_SIZE,
    open && !!repository,
  )

  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const scans = data?.items ?? []

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) setPage(1)
    onOpenChange(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{repository?.name ?? 'Scans'}</DialogTitle>
          <DialogDescription>Scan history for this repository</DialogDescription>
        </DialogHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Created</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Error</TableHead>
              <TableHead className="text-right">Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isPending ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center">
                  <Spinner className="mx-auto" />
                </TableCell>
              </TableRow>
            ) : scans.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  No scans yet
                </TableCell>
              </TableRow>
            ) : (
              scans.map((scan) => (
                <TableRow key={scan.id}>
                  <TableCell className="whitespace-nowrap">{formatDateTime(scan.created_at)}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_BADGE_VARIANT[scan.status]}>{scan.status}</Badge>
                  </TableCell>
                  <TableCell
                    className="max-w-[200px] truncate text-destructive"
                    title={scan.error ?? undefined}
                  >
                    {scan.error ?? '—'}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="View scan details"
                      title="View scan details"
                      onClick={() => {
                        // TODO: implement scan detail view
                      }}
                    >
                      <Info className="size-5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        {!isPending && scans.length > 0 && totalPages > 1 && (
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  href="#"
                  aria-disabled={page === 1}
                  className={page === 1 ? 'pointer-events-none opacity-50' : undefined}
                  onClick={(e) => {
                    e.preventDefault()
                    if (page > 1) setPage(page - 1)
                  }}
                />
              </PaginationItem>
              <PaginationItem>
                <PaginationNext
                  href="#"
                  aria-disabled={page === totalPages}
                  className={page === totalPages ? 'pointer-events-none opacity-50' : undefined}
                  onClick={(e) => {
                    e.preventDefault()
                    if (page < totalPages) setPage(page + 1)
                  }}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        )}
      </DialogContent>
    </Dialog>
  )
}
