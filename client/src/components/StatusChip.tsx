import type { InvoiceStatus } from '../api.ts'

export function StatusChip({ status }: { status: InvoiceStatus }) {
  return (
    <span className={`chip chip--${status}`}>
      <span className="chip__dot" aria-hidden="true" />
      {status}
    </span>
  )
}
