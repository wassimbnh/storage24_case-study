import { useEffect, useState } from 'react'
import './App.css'
import { fetchInvoices, type Invoice } from './api.ts'
import { InvoiceCard } from './components/InvoiceCard.tsx'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'loaded'; invoices: Invoice[] }

function App() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })

  useEffect(() => {
    let cancelled = false
    fetchInvoices()
      .then((invoices) => !cancelled && setState({ kind: 'loaded', invoices }))
      .catch(
        (error: unknown) =>
          !cancelled &&
          setState({ kind: 'error', message: error instanceof Error ? error.message : String(error) }),
      )
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="page">
      <header className="page__header">
        <p className="page__eyebrow">Payment Status Trigger</p>
        <h1 className="page__title">Invoices</h1>
        {state.kind === 'loaded' && (
          <p className="page__subtitle">
            {state.invoices.length} {state.invoices.length === 1 ? 'invoice' : 'invoices'}
          </p>
        )}
      </header>

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
