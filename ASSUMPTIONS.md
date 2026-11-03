# Assumptions

| Assumption | Basis | Impact if wrong | In a real deployment |
|---|---|---|---|
| The trigger runs on demand, not automatically. One click on **Run process** in the UI calls `POST /run`, which syncs `payment_status_history` into the tracking table and then processes the pending rows. Nothing runs on a timer, a database trigger or a status-change event. | Logical inference from the brief. A scheduler/cron job is explicitly out of scope, the seed dates are fixed so no clock-based logic is wanted, and the deliverable is a UI that shows the results. A button makes each pass visible and repeatable for the demo, and **Reset** (`POST /reset`) lets it be replayed from scratch. | Overdue invoices only get a payment link when someone presses the button. If nobody does, customers are not asked to pay. | `/run` would be called automatically, either by short polling (a job calling it every few minutes) or by a webhook/event fired whenever a row is written to `payment_status_history`. The sync and processing logic would stay as is: both are idempotent, and the pending -> processing claim stops overlapping runs from creating two links for the same history row. |
| The six inputs given to the Stripe mock (`invoiceId`, `amountCents`, `currency`, `customerEmail`, `stripeCustomerId`, `settlementBankAccountId`) are enough to create a payment link. The mock logs them and returns a fake URL and a fake `plink_` ID. | Taken from the brief, which defines these six inputs. Checked against the Stripe API reference ([Create a payment link](https://docs.stripe.com/api/payment-link/create), [Create a Checkout Session](https://docs.stripe.com/api/checkout/sessions/create), API version 2026-10-28): they cover what to charge but do not map one-to-one onto real Stripe parameters. | A real integration could not be built from these six values alone. Stripe has no parameter that takes a bank account ID, so routing would need a Stripe account ID per legal entity, which the schema does not store. The Payment Links API has no `customer` or `customer_email` parameter, so the email and Stripe customer ID could not be attached to the link. Without an idempotency key, a retried request after a timeout could create a second link. | `POST /v1/payment_links` with: `line_items[0][price_data][unit_amount]` = `amountCents`, `line_items[0][price_data][currency]` = lowercase `currency`, `line_items[0][price_data][product_data][name]` = "Invoice 1002", `line_items[0][quantity]` = 1. `metadata[invoice_id]`, `metadata[history_id]` and `metadata[customer_id]` would let the webhook find the invoice; Stripe copies link metadata onto its Checkout Sessions. `restrictions[completion_sessions][limit]` = 1 would stop the link from being paid twice. Each legal entity would be a connected account (`acct_...`) with its bank account set as the payout account, passed as `on_behalf_of` and `transfer_data[destination]`. An `Idempotency-Key` header derived from `history_id` would make retries safe. To pre-fill or attach the customer, a Checkout Session (`mode=payment`, `customer` or `customer_email`, `success_url`) would replace the payment link, with the trade-off that its URL expires after at most 24 hours. |
| A payment link is created once per history row, not once per invoice. The tracking table has `UNIQUE(history_id)`, and sync uses `INSERT OR IGNORE`, so the same `open -> overdue` event can never produce two links, however many times **Run process** is pressed. If an invoice went `open -> overdue -> open -> overdue`, each `open -> overdue` row would get its own link. | Logical inference from the brief: the event source is `payment_status_history`, and it asks for one tracking row per history row with a unique `history_id`. Re-running must never create a second link for the same history row. | If the business wants at most one active link per invoice, an invoice that goes overdue a second time would get a second link while the first is still payable, and the customer could pay twice. | Before creating a new link for an invoice, deactivate the previous one (`POST /v1/payment_links/{id}` with `active=false`) and record it on the old tracking row. Alternatively, reuse the existing active link if the amount is unchanged. Either way, the webhook should check that the invoice is still unpaid before marking a payment as settling it. |
| A row left in `processing` is never retried automatically. A row is claimed (`pending -> processing`) before Stripe is called. If the server crashes after the call but before the result is saved, the row stays in `processing`, and `process_pending` only picks up `pending` rows. | Logical inference. With the mock there is no way to know whether a link was created before the crash. Retrying blindly could create a second link for the same history row, which the brief forbids. A missing link can be fixed by hand; a duplicate one could be paid twice. | An invoice can stay without a payment link until someone notices the stuck row. In the demo, only **Reset** clears it. | A reconciliation job would look for rows in `processing` older than a few minutes and ask Stripe whether a link already exists for that `history_id` (by metadata, or by replaying the request with the same `Idempotency-Key`, which returns the original result instead of a new link). The row is then set to `created` with the existing link, or put back to `pending` if none exists. |

## Trigger condition

A payment link is only useful when a customer owes money and has missed the due date. The `open -> overdue` transition is the exact moment that happens, so it is the event we react to.

The other transitions in the seed do not need a link:

- `NULL -> open`: the invoice was just created and is not due yet.
- `open -> paid`: the customer already paid.
- `open -> void`: the invoice was cancelled, so nothing is owed.

We read the event from `payment_status_history` rather than `invoices.status`, because the history records *when* the status changed, while the snapshot only shows the current value. Before creating the link we still check that the invoice is overdue *now*. If it was paid or voided since the event, the event is stale and we skip it.

In the seed, only history row 4 (invoice 1002) qualifies.

## Routing logic

The money must go to the bank account of the company that owns the park where the customer rents storage. We follow the foreign keys:

```
invoices.park_id -> parks.legal_entity_id -> bank_accounts (same legal_entity_id, same currency)
```

1. The invoice tells us which park it belongs to.
2. The park tells us which legal entity owns it.
3. We pick that legal entity's bank account in the invoice currency.

We never route via the customer: customer 100 has invoices at München Nord and München Süd, which belong to two different legal entities. If no account or more than one account matches, the row fails with a clear error instead of guessing.

For invoice 1002: park 11 (München Süd) -> legal entity 2 -> bank account 2 (Commerzbank, EUR).

## Design note: the two non-implemented triggers

### 1. Receipt-of-payment notification to the customer

**Trigger**

The event is a tracking row reaching `created`, meaning the link exists and is saved. The email is queued in the same transaction that stores the link, and a worker sends it after the commit. The payment-link job never calls the email provider itself.

**Flow**

1. In the same transaction as the `created` update, insert a `link_emails` row as `pending`, with a unique key on the history ID.
2. The worker claims it (`pending -> sending`) and checks that the invoice is still overdue. If it is paid or void, it skips with a reason.
3. It loads the customer's email from the invoice's customer and sends the link through the email provider, with an idempotency key.
4. It sets `sent` once the provider accepts the message. The provider's delivery webhook later moves it to `delivered`.

**What could go wrong and how we guard against it**

| Risk | Guard |
|---|---|
| Delivered to spam, or looks like phishing | Send from our own domain with SPF, DKIM and DMARC set up. Use a branded template that names the park and the invoice number, and let the link point to Stripe's known domain (`buy.stripe.com`). |
| Never opened | Track opens and clicks through the provider. If the link is still unpaid after a few days, send one reminder and show the open invoice in the customer portal. |
| Invoice paid before the email goes out | The worker checks that the invoice is still overdue right before sending, and skips with a reason if it is paid or void. |

### 2. Stripe webhook success -> update invoice status in the DB

**Trigger**

Stripe calls our endpoint (`POST /webhooks/stripe`) with `checkout.session.completed` when the customer pays through the link. Card payments arrive with `payment_status = paid`.

**Flow**

1. Verify the `Stripe-Signature` header against the endpoint secret, using the raw request body. Reject anything that fails.
2. Insert the event ID into a `stripe_events` table with a unique key. If it is already there, the event was handled before: return `200` and stop.
3. Find the invoice from the session metadata (`invoice_id`, `history_id`) set when the link was created, never from the customer.
4. Check that the amount and currency paid match the invoice.
5. In one transaction: `UPDATE invoices SET status = 'paid' WHERE id = ? AND status = 'overdue'`, and insert an `overdue -> paid` row into `payment_status_history`.
6. Deactivate the payment link (`active = false`) so it cannot be paid again.
7. Return `200` quickly. Stripe treats a slow or failed response as a failure and retries.

**What could go wrong and how we guard against it**

| Risk | Guard |
|---|---|
| The same event is delivered twice (Stripe delivers at least once) | Save each event ID with a unique key. If it is already saved, ignore the event. |
| The amount or currency paid does not match the invoice | Do not mark the invoice as paid. Flag it for manual review. |
| Our endpoint is down when Stripe calls | Stripe retries the event for up to 3 days. A daily job also checks paid sessions in Stripe and fixes any invoice still marked overdue. |

## Out of scope / what we'd do next

**Invoices live in our database.** A background worker reads new rows from `payment_status_history` with a cursor (`id > last_processed_id`) every minute and calls the existing sync and process steps.

**Invoices live on another system.** The billing system notifies us through a webhook, `POST /webhooks/invoice-status`, whenever an invoice status changes, and we run the process.

### Other things left out on purpose

- The Stripe payment webhook and the customer email: covered by the design note above.
- Authentication on the API endpoints.
