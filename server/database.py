import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"

TRACKING_STATUSES = ("pending", "processing", "created", "failed", "skipped")

# Our own table: created empty here, never in schema.sql and never seeded.
CREATE_TRACKING_TABLE = f"""
CREATE TABLE IF NOT EXISTS payment_link_tracking (
    id INTEGER PRIMARY KEY,
    history_id INTEGER NOT NULL UNIQUE REFERENCES payment_status_history(id),
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    status TEXT NOT NULL CHECK (status IN ({", ".join(f"'{s}'" for s in TRACKING_STATUSES)})),
    reason TEXT,  -- why a row was skipped
    error TEXT,   -- why a row failed
    url TEXT,
    stripe_payment_link_id TEXT,
    settlement_bank_account_id INTEGER REFERENCES bank_accounts(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> sqlite3.Connection:
    # In-memory DB rebuilt on every startup: schema.sql creates tables and seeds
    # data without IF NOT EXISTS, so it can only run against a fresh database.
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(CREATE_TRACKING_TABLE)
    conn.commit()
    return conn


def list_tracking_rows(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM payment_link_tracking ORDER BY history_id")
    return [dict(row) for row in rows]


def reset_tracking(conn: sqlite3.Connection) -> int:
    """Delete all tracking rows. Seeded tables are left untouched."""
    with conn:
        cursor = conn.execute("DELETE FROM payment_link_tracking")
    return cursor.rowcount
