Payment Status Trigger: Case Study

Take-home exercise: detect invoices that just became overdue, create a mock Stripe payment link routed to the right bank account, and show the results in a UI. The submission must be anonymous: no personal data (name, email, phone, username paths) in code, comments, docs or prompts.

Stack
Backend: Python, FastAPI, SQLite. main.py holds only the app and its endpoints.
Frontend: React + TypeScript (Vite). It only reads results and never contains business logic.
No real Stripe and no outside network calls.
Data
schema.sql is loaded into SQLite at startup. Do not edit that file or change the seeded tables.
Our own tables are created in a separate init step, never in schema.sql.
Trigger rule
The event source is payment_status_history, not the invoices.status snapshot.
A history row qualifies when old_status = open and new_status = overdue.
It only fires if the invoice's current status is still overdue. Otherwise the event is stale and is skipped.
No time windows or clock-based logic: the seed dates are fixed.
In the seed only history row 4 (invoice 1002) qualifies. The NULL -> open rows, open -> paid (1001) and open -> void (1004) never trigger.
Tracking table
Created empty at init, never seeded. One row per history row, with a unique history_id.
Columns: history_id, invoice_id, status, reason or error, url, stripe_payment_link_id, settlement_bank_account_id, created_at, updated_at.
Statuses: pending (queued), processing (claimed), created, failed, skipped.
Processing flow
Sync: for each history row without a tracking row, classify it in code and insert it. pending if it is open -> overdue, otherwise skipped with a reason. Idempotent.
Process each pending row. If the invoice is no longer overdue, mark it skipped (stale event).
Claim with a conditional update (pending -> processing) and continue only if exactly one row changed. Claim before calling Stripe.
Resolve routing, call the Stripe mock, then set the row to created (url, link id, bank account) or failed (error).
Errors are handled per row, so one failure never blocks the others.
Re-running must never create a second link for the same history row.
A reset endpoint clears the tracking table so the demo can be rerun from scratch.
Routing
Follow invoice -> park -> legal entity -> bank account.
Never route via the customer. Customer 100 has invoices at two parks that belong to different legal entities.
Match the bank account currency to the invoice currency.
If zero or more than one account matches, fail with a clear error. Never guess.
Stripe mock
Same inputs as the brief: invoiceId, amountCents, currency, customerEmail, stripeCustomerId (nullable), settlementBankAccountId.
Log the inputs and return a fake URL and a fake payment link ID.
A null stripeCustomerId is passed through unchanged.
Code rules
Separate modules for database setup, sync, processing, routing and the Stripe mock.
Clear names, short comments only where the reason is not obvious, explicit error messages.
Stay in scope. Do not build a scheduler or cron job, SSE, the Stripe webhook handler, or the customer receipt. Those two are covered by a design note only.
Acceptance checks
First run: 7 tracking rows, 6 skipped, 1 created.
The created row is invoice 1002, routed to bank account 2 (Commerzbank, München Süd).
Running again adds no rows and no second link.
Reset, then run: the same 7 rows are recreated once.
Deliverables (only when asked)
Assumptions document using the Section 5 template of the brief.
Design note for the Stripe webhook and the customer receipt: trigger, what could go wrong, how to guard against it.
The code, plus the exported AI session transcript.