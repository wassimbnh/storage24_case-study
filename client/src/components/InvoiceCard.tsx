import type { Invoice } from '../api.ts'
import { formatAmount, formatDate } from '../format.ts'
import { StatusChip } from './StatusChip.tsx'

export function InvoiceCard({ invoice }: { invoice: Invoice }) {
  return (
    <article className={`invoice-card invoice-card--${invoice.status}`}>
      <header className="invoice-card__header">
        <span className="invoice-card__id">#{invoice.id}</span>
        <StatusChip status={invoice.status} />
      </header>

      <h2 className="invoice-card__customer">{invoice.customer_name}</h2>
      <p className="invoice-card__amount">{formatAmount(invoice.amount_cents, invoice.currency)}</p>

      <dl className="invoice-card__details">
        <div>
          <dt>Currency</dt>
          <dd>{invoice.currency}</dd>
        </div>
        <div>
          <dt>Due date</dt>
          <dd>
            <time dateTime={invoice.due_date}>{formatDate(invoice.due_date)}</time>
          </dd>
        </div>
      </dl>
    </article>
  )
}
