export type InvoiceStatus = 'open' | 'overdue' | 'paid' | 'void'

export interface Invoice {
  id: number
  customer_name: string
  status: InvoiceStatus
  amount_cents: number
  currency: string
  due_date: string
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`)
  if (!response.ok) {
    throw new Error(`GET ${path} failed with ${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export function fetchInvoices(): Promise<Invoice[]> {
  return getJson<Invoice[]>('/invoices')
}
