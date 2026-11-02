import sqlite3


class RoutingError(Exception):
    """The settlement bank account for an invoice cannot be determined unambiguously."""


def resolve_settlement_bank_account(conn: sqlite3.Connection, invoice_id: int) -> int:
    """Route invoice -> park -> legal entity -> bank account in the invoice currency.

    Never routes via the customer: one customer can have invoices at parks owned
    by different legal entities.
    """
    invoice = conn.execute(
        """
        SELECT i.currency, p.id AS park_id, p.legal_entity_id
        FROM invoices i
        LEFT JOIN parks p ON p.id = i.park_id
        WHERE i.id = ?
        """,
        (invoice_id,),
    ).fetchone()
    if invoice is None:
        raise RoutingError(f"invoice {invoice_id} not found")
    if invoice["park_id"] is None:
        raise RoutingError(f"invoice {invoice_id}: park not found")

    legal_entity_id = invoice["legal_entity_id"]
    currency = invoice["currency"]
    accounts = conn.execute(
        "SELECT id FROM bank_accounts WHERE legal_entity_id = ? AND currency = ? ORDER BY id",
        (legal_entity_id, currency),
    ).fetchall()

    if not accounts:
        raise RoutingError(
            f"invoice {invoice_id}: no {currency} bank account for legal entity {legal_entity_id}"
        )
    if len(accounts) > 1:
        ids = ", ".join(str(a["id"]) for a in accounts)
        raise RoutingError(
            f"invoice {invoice_id}: {len(accounts)} {currency} bank accounts for legal entity "
            f"{legal_entity_id} (ids {ids}); refusing to guess"
        )
    return accounts[0]["id"]
