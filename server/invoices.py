import sqlite3


def list_invoices(conn: sqlite3.Connection) -> list[dict]:
    """Invoices with the customer name and, if one was created, the payment link. For display only."""
    rows = conn.execute(
        """
        SELECT i.id, c.full_name AS customer_name, i.status, i.amount_cents,
               i.currency, i.due_date,
               p.name AS park_name, p.city AS park_city,
               t.history_id, t.url, t.stripe_payment_link_id, t.updated_at AS link_created_at,
               b.id AS bank_account_id, b.bank_name, b.iban, b.currency AS bank_currency,
               le.id AS legal_entity_id, le.name AS legal_entity_name
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        JOIN parks p ON p.id = i.park_id
        -- Latest created link for the invoice, in case it went open -> overdue more than once.
        LEFT JOIN payment_link_tracking t ON t.id = (
            SELECT id FROM payment_link_tracking
            WHERE invoice_id = i.id AND status = 'created'
            ORDER BY history_id DESC
            LIMIT 1
        )
        LEFT JOIN bank_accounts b ON b.id = t.settlement_bank_account_id
        LEFT JOIN legal_entities le ON le.id = b.legal_entity_id
        ORDER BY i.id
        """
    )
    return [_to_invoice(row) for row in rows]


def _to_invoice(row: sqlite3.Row) -> dict:
    payment_link = None
    if row["stripe_payment_link_id"] is not None:
        payment_link = {
            "id": row["stripe_payment_link_id"],
            "url": row["url"],
            "history_id": row["history_id"],
            "created_at": row["link_created_at"],
            "park": {"name": row["park_name"], "city": row["park_city"]},
            "bank_account": {
                "id": row["bank_account_id"],
                "bank_name": row["bank_name"],
                "iban": row["iban"],
                "currency": row["bank_currency"],
                "legal_entity": {"id": row["legal_entity_id"], "name": row["legal_entity_name"]},
            },
        }
    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "status": row["status"],
        "amount_cents": row["amount_cents"],
        "currency": row["currency"],
        "due_date": row["due_date"],
        "payment_link": payment_link,
    }
