import logging
import sqlite3

import stripe_mock
from database import utc_now
from routing import resolve_settlement_bank_account

logger = logging.getLogger(__name__)


def process_pending(conn: sqlite3.Connection) -> dict:
    """Turn every pending tracking row into created, failed or skipped.

    Each row is handled on its own, so one failure never blocks the others.
    Rows left in 'processing' (e.g. after a crash mid-call) are not retried here:
    retrying could create a second link for the same history row.
    """
    pending_ids = [
        row["id"]
        for row in conn.execute(
            "SELECT id FROM payment_link_tracking WHERE status = 'pending' ORDER BY history_id"
        )
    ]

    counts = {"created": 0, "failed": 0, "skipped": 0, "not_claimed": 0}
    for tracking_id in pending_ids:
        counts[_process_row(conn, tracking_id)] += 1
    return counts


def _process_row(conn: sqlite3.Connection, tracking_id: int) -> str:
    invoice = conn.execute(
        """
        SELECT i.id, i.amount_cents, i.currency, i.status, c.email, c.stripe_customer_id
        FROM payment_link_tracking t
        JOIN invoices i ON i.id = t.invoice_id
        JOIN customers c ON c.id = i.customer_id
        WHERE t.id = ?
        """,
        (tracking_id,),
    ).fetchone()

    # The history row says open -> overdue, but the event only fires if that is still true now.
    if invoice["status"] != "overdue":
        reason = f"stale event: invoice {invoice['id']} is now {invoice['status']}, not overdue"
        changed = _transition(conn, tracking_id, "pending", "skipped", reason=reason)
        return "skipped" if changed else "not_claimed"

    # Claim before calling Stripe; if another run claimed it first, leave it alone.
    if not _transition(conn, tracking_id, "pending", "processing"):
        return "not_claimed"

    try:
        bank_account_id = resolve_settlement_bank_account(conn, invoice["id"])
        link = stripe_mock.create_payment_link(
            invoice_id=invoice["id"],
            amount_cents=invoice["amount_cents"],
            currency=invoice["currency"],
            customer_email=invoice["email"],
            stripe_customer_id=invoice["stripe_customer_id"],
            settlement_bank_account_id=bank_account_id,
        )
    except Exception as exc:
        error = str(exc) or type(exc).__name__
        logger.warning("tracking row %s failed: %s", tracking_id, error)
        _transition(conn, tracking_id, "processing", "failed", error=error)
        return "failed"

    _transition(
        conn,
        tracking_id,
        "processing",
        "created",
        url=link["url"],
        stripe_payment_link_id=link["id"],
        settlement_bank_account_id=bank_account_id,
    )
    return "created"


def _transition(
    conn: sqlite3.Connection, tracking_id: int, from_status: str, to_status: str, **fields
) -> bool:
    """Conditionally move a row from one status to another. True if exactly one row changed."""
    assignments = ", ".join(f"{name} = ?" for name in fields)
    sql = (
        "UPDATE payment_link_tracking SET status = ?, updated_at = ?"
        + (f", {assignments}" if assignments else "")
        + " WHERE id = ? AND status = ?"
    )
    with conn:
        cursor = conn.execute(
            sql, (to_status, utc_now(), *fields.values(), tracking_id, from_status)
        )
    return cursor.rowcount == 1
