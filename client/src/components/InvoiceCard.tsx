import { useState } from 'react'
import type { Invoice } from '../api.ts'
import { formatAmount, formatDate } from '../format.ts'
import { PaymentLinkModal } from './PaymentLinkModal.tsx'
import { StatusChip } from './StatusChip.tsx'

export function InvoiceCard({ invoice }: { invoice: Invoice }) {
  const [linkOpen, setLinkOpen] = useState(false)
  const link = invoice.payment_link

  return (
    <article
      className={`invoice-card invoice-card--${invoice.status} ${link ? 'invoice-card--has-link' : ''}`}
    >
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

      {link && (
        <div className="invoice-card__link">
          <span className="link-flag">
            <span className="link-flag__icon" aria-hidden="true">
              ✓
            </span>
            Payment link created
          </span>
          <button
            type="button"
            className="btn btn--link-action"
            onClick={() => setLinkOpen(true)}
            aria-haspopup="dialog"
          >
            View link &amp; routing
          </button>
        </div>
      )}

      {!link && invoice.no_link_reason && (
        <div className="invoice-card__no-link">
          <span className="invoice-card__no-link-title">No payment link</span>
          <span className="invoice-card__no-link-reason">{invoice.no_link_reason}</span>
        </div>
      )}

      {link && linkOpen && (
        <PaymentLinkModal invoice={invoice} link={link} onClose={() => setLinkOpen(false)} />
      )}
    </article>
  )
}
