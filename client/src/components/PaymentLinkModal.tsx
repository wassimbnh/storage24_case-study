import { useEffect, useRef, useState } from 'react'
import type { Invoice, PaymentLink } from '../api.ts'
import { formatAmount, formatDateTime } from '../format.ts'

interface PaymentLinkModalProps {
  invoice: Invoice
  link: PaymentLink
  onClose: () => void
}

export function PaymentLinkModal({ invoice, link, onClose }: PaymentLinkModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [copied, setCopied] = useState(false)
  const { bank_account: account, park } = link
  const titleId = `payment-link-title-${invoice.id}`

  // Native <dialog> gives focus trapping, Esc to close and a backdrop for free.
  // No close() in a cleanup: in StrictMode that queues a 'close' event that fires after the
  // re-run and shuts the modal again. Unmounting removes the dialog from the page anyway.
  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(link.url)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard can be unavailable (e.g. non-secure context); the URL stays selectable.
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="modal"
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => {
        // A click on the backdrop lands on the <dialog> element itself.
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="modal__panel">
        <header className="modal__header">
          <div>
            <p className="modal__eyebrow">Invoice #{invoice.id}</p>
            <h2 id={titleId} className="modal__title">
              Payment link
            </h2>
            <p className="modal__subtitle">
              {invoice.customer_name} · {formatAmount(invoice.amount_cents, invoice.currency)}
            </p>
          </div>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <section className="modal__section">
          <h3 className="modal__label">Generated link (mock)</h3>
          <div className="link-box">
            <code className="link-box__url">{link.url}</code>
          </div>
        </section>

        <section className="modal__section">
          <h3 className="modal__label">Routed to</h3>
          <dl className="account">
            <div className="account__row">
              <dt>Bank account</dt>
              <dd>
                #{account.id} {account.bank_name}
              </dd>
            </div>
            <div className="account__row">
              <dt>IBAN</dt>
              <dd className="account__mono">{account.iban}</dd>
            </div>
            <div className="account__row">
              <dt>Currency</dt>
              <dd>{account.currency}</dd>
            </div>
            <div className="account__row">
              <dt>Account owner</dt>
              <dd>{account.legal_entity.name}</dd>
            </div>
            <div className="account__row">
              <dt>Invoice park</dt>
              <dd>
                {park.name} · {park.city}
              </dd>
            </div>
          </dl>
        </section>

        <footer className="modal__footer">
          <button type="button" className="btn btn--primary" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </dialog>
  )
}
