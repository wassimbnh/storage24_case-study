export type InvoiceStatus = 'open' | 'overdue' | 'paid' | 'void'

export interface Invoice {
  id: number
  customer_name: string
  status: InvoiceStatus
  amount_cents: number
  currency: string
  due_date: string
  payment_link: PaymentLink | null
}

/** The mock Stripe link created for an invoice and the account it settles into. */
export interface PaymentLink {
  id: string
  url: string
  history_id: number
  created_at: string
  park: { name: string; city: string }
  bank_account: {
    id: number
    bank_name: string
    iban: string
    currency: string
    legal_entity: { id: number; name: string }
  }
}

export interface SyncResult {
  inserted: number
  pending: number
  skipped: number
}

export interface ProcessResult {
  created: number
  failed: number
  skipped: number
  not_claimed: number
}

export interface RunResult {
  sync: SyncResult
  process: ProcessResult
}

export interface ResetResult {
  deleted: number
}

async function request<T>(method: 'GET' | 'POST', path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { method })
  if (!response.ok) {
    throw new Error(`${method} ${path} failed with ${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export function fetchInvoices(): Promise<Invoice[]> {
  return request<Invoice[]>('GET', '/invoices')
}

export function runTrigger(): Promise<RunResult> {
  return request<RunResult>('POST', '/run')
}

export function resetTracking(): Promise<ResetResult> {
  return request<ResetResult>('POST', '/reset')
}
