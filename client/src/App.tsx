import { useEffect, useState } from 'react'
import './App.css'
import {
  fetchInvoices,
  resetTracking,
  runTrigger,
  type Invoice,
  type ResetResult,
  type RunResult,
} from './api.ts'
import { ActionBar, type BusyAction } from './components/ActionBar.tsx'
import { InvoiceCard } from './components/InvoiceCard.tsx'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'loaded'; invoices: Invoice[] }

type LastAction =
  | { kind: 'run'; result: RunResult }
  | { kind: 'reset'; result: ResetResult }
  | { kind: 'error'; message: string }

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function invoices(count: number): string {
  return `${count} ${count === 1 ? 'invoice' : 'invoices'}`
}

function describeRun({ process }: RunResult): string {
  const parts: string[] = []
  if (process.created > 0) parts.push(`Payment link created for ${invoices(process.created)}`)
  if (process.failed > 0) parts.push(`${invoices(process.failed)} failed`)
  return parts.length > 0 ? parts.join(' · ') : 'No new invoices to process'
}

function isFailure(action: LastAction): boolean {
  return action.kind === 'error' || (action.kind === 'run' && action.result.process.failed > 0)
}

function describeReset({ deleted }: ResetResult): string {
  return `Reset: ${deleted} tracking ${deleted === 1 ? 'row' : 'rows'} deleted`
}

function App() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [busy, setBusy] = useState<BusyAction>(null)
  const [lastAction, setLastAction] = useState<LastAction | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchInvoices()
      .then((invoices) => !cancelled && setState({ kind: 'loaded', invoices }))
      .catch((error: unknown) => !cancelled && setState({ kind: 'error', message: errorMessage(error) }))
    return () => {
      cancelled = true
    }
  }, [])

  async function handleRun() {
    setBusy('run')
    try {
      setLastAction({ kind: 'run', result: await runTrigger() })
    } catch (error) {
      setLastAction({ kind: 'error', message: errorMessage(error) })
    } finally {
      setBusy(null)
    }
  }

  async function handleReset() {
    setBusy('reset')
    try {
      setLastAction({ kind: 'reset', result: await resetTracking() })
    } catch (error) {
      setLastAction({ kind: 'error', message: errorMessage(error) })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <p className="page__eyebrow">Payment Status Trigger</p>
          <h1 className="page__title">Invoices</h1>
          {state.kind === 'loaded' && (
            <p className="page__subtitle">
              {state.invoices.length} {state.invoices.length === 1 ? 'invoice' : 'invoices'}
            </p>
          )}
        </div>
        <ActionBar busy={busy} onRun={handleRun} onReset={handleReset} />
      </header>

      {lastAction && (
        <div
          className={`notice notice--banner ${isFailure(lastAction) ? 'notice--error' : 'notice--success'}`}
          role={isFailure(lastAction) ? 'alert' : 'status'}
        >
          {lastAction.kind === 'run' && describeRun(lastAction.result)}
          {lastAction.kind === 'reset' && describeReset(lastAction.result)}
          {lastAction.kind === 'error' && `Action failed: ${lastAction.message}`}
        </div>
      )}

      <main>
        {state.kind === 'loading' && (
          <div className="card-grid" aria-busy="true" aria-label="Loading invoices">
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="invoice-card invoice-card--skeleton" />
            ))}
          </div>
        )}

        {state.kind === 'error' && (
          <div className="notice notice--error" role="alert">
            <strong>Could not load invoices.</strong>
            <span>{state.message}. Is the backend running on port 8000?</span>
          </div>
        )}

        {state.kind === 'loaded' && state.invoices.length === 0 && (
          <div className="notice">No invoices found.</div>
        )}

        {state.kind === 'loaded' && state.invoices.length > 0 && (
          <div className="card-grid">
            {state.invoices.map((invoice) => (
              <InvoiceCard key={invoice.id} invoice={invoice} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
