import sqlite3

from database import utc_now


def classify(old_status: str | None, new_status: str) -> tuple[str, str | None]:
    """Return (tracking status, skip reason) for one history row."""
    if old_status == "open" and new_status == "overdue":
        return "pending", None
    return "skipped", f"transition {old_status or 'NULL'} -> {new_status} is not open -> overdue"


def sync_tracking(conn: sqlite3.Connection) -> dict:
    """Insert one tracking row for every history row that has none yet. Idempotent."""
    untracked = conn.execute(
        """
        SELECT h.id, h.invoice_id, h.old_status, h.new_status
        FROM payment_status_history h
        LEFT JOIN payment_link_tracking t ON t.history_id = h.id
        WHERE t.id IS NULL
        ORDER BY h.id
        """
    ).fetchall()

    counts = {"pending": 0, "skipped": 0}
    now = utc_now()
    with conn:
        for row in untracked:
            status, reason = classify(row["old_status"], row["new_status"])
            # OR IGNORE + UNIQUE(history_id) guards against a concurrent sync inserting the same row.
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO payment_link_tracking
                    (history_id, invoice_id, status, reason, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row["id"], row["invoice_id"], status, reason, now, now),
            )
            if cursor.rowcount == 1:
                counts[status] += 1

    return {"inserted": counts["pending"] + counts["skipped"], **counts}
