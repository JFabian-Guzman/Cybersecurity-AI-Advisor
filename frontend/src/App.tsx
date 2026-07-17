import { useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ConnectRepositoryForm } from './features/components/ConnectRepositoryForm'
import { ScanStatus } from './features/components/ScanStatus'
import { useScanQuery } from './features/api/get-scan'

function App() {
  const [scanId, setScanId] = useState(() =>
    new URLSearchParams(window.location.search).get('scanId'),
  )

  const { data: scan } = useScanQuery(scanId)

  function handleConnected(newScanId: string) {
    setScanId(newScanId)
    const params = new URLSearchParams(window.location.search)
    params.set('scanId', newScanId)
    window.history.replaceState(null, '', `?${params.toString()}`)
  }

  function handleReset() {
    setScanId(null)
    window.history.replaceState(null, '', window.location.pathname)
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 bg-grid-pattern" />
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-[#F7931A] opacity-10 blur-[120px]" />
      <div className="pointer-events-none absolute right-0 bottom-0 h-[500px] w-[500px] rounded-full bg-[#FFD600] opacity-[0.07] blur-[130px]" />

      <main className="relative mx-auto flex min-h-screen max-w-4xl flex-col gap-8 px-6 py-16">
        <header className="flex flex-col items-center gap-3 text-center">
          <div className="flex items-center gap-3">
            <span className="flex items-center justify-center rounded-lg border border-[#F7931A]/50 bg-[#F7931A]/20 p-2 shadow-[0_0_20px_-5px_rgba(247,147,26,0.6)]">
              <ShieldCheck className="size-7 text-[#F7931A] md:size-9" strokeWidth={1.75} />
            </span>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl">
              CyberSecurity{' '}
              <span className="bg-gradient-to-r from-[#F7931A] to-[#FFD600] bg-clip-text text-transparent">
                Advisor
              </span>
            </h1>
          </div>
          <p className="text-[#94A3B8]">Security findings for your scanned repository</p>
        </header>

        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <CardTitle>Findings</CardTitle>
              <CardDescription>
                {scanId ? (
                  <>
                    {scan?.repository_name ? `${scan.repository_name} - ` : ''}
                    Scan <span className="font-mono">{scanId}</span>
                  </>
                ) : (
                  'Connect a repository to scan'
                )}
              </CardDescription>
            </div>
            {scanId && (
              <Button variant="default" className="shrink-0" onClick={handleReset}>
                Scan another repository
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {scanId ? (
              <ScanStatus scanId={scanId} />
            ) : (
              <ConnectRepositoryForm onConnected={handleConnected} />
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

export default App
