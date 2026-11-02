import sqlite3


def list_invoices(conn: sqlite3.Connection) -> list[dict]:
    """Invoices with the customer name, for display only."""
    rows = conn.execute(
        """
        SELECT i.id, c.full_name AS customer_name, i.status, i.amount_cents,
               i.currency, i.due_date
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        ORDER BY i.id
        """
    )
    return [dict(row) for row in rows]
