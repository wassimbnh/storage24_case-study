import pytest

from database import list_tracking_rows, reset_tracking
from sync import classify, sync_tracking

SEED_HISTORY_IDS = [1, 2, 3, 4, 5, 6, 7]
QUALIFYING_HISTORY_ID = 4  # invoice 1002: open -> overdue


# --- classify -------------------------------------------------------------


def test_classify_open_to_overdue_is_pending():
    assert classify("open", "overdue") == ("pending", None)


@pytest.mark.parametrize(
    ("old_status", "new_status"),
    [
        (None, "open"),
        ("open", "paid"),
        ("open", "void"),
        ("overdue", "paid"),
        (None, "overdue"),  # overdue without coming from open does not qualify
        ("paid", "overdue"),
    ],
)
def test_classify_other_transitions_are_skipped_with_reason(old_status, new_status):
    status, reason = classify(old_status, new_status)
    assert status == "skipped"
    assert reason
    assert new_status in reason


def test_classify_null_old_status_is_named_in_reason():
    _, reason = classify(None, "open")
    assert "NULL -> open" in reason


# --- sync_tracking --------------------------------------------------------


def test_tracking_table_starts_empty(db):
    assert list_tracking_rows(db) == []


def test_first_sync_creates_one_row_per_history_row(db):
    result = sync_tracking(db)

    assert result == {"inserted": 7, "pending": 1, "skipped": 6}
    rows = list_tracking_rows(db)
    assert [row["history_id"] for row in rows] == SEED_HISTORY_IDS


def test_only_history_row_4_is_pending(db):
    sync_tracking(db)

    pending = [row for row in list_tracking_rows(db) if row["status"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["history_id"] == QUALIFYING_HISTORY_ID
    assert pending[0]["invoice_id"] == 1002
    assert pending[0]["reason"] is None


def test_skipped_rows_have_a_reason(db):
    sync_tracking(db)

    skipped = [row for row in list_tracking_rows(db) if row["status"] == "skipped"]
    assert len(skipped) == 6
    assert all(row["reason"] for row in skipped)


def test_sync_copies_invoice_id_from_history(db):
    sync_tracking(db)

    history = {
        row["id"]: row["invoice_id"]
        for row in db.execute("SELECT id, invoice_id FROM payment_status_history")
    }
    for row in list_tracking_rows(db):
        assert row["invoice_id"] == history[row["history_id"]]


def test_sync_does_not_fill_processing_fields(db):
    sync_tracking(db)

    for row in list_tracking_rows(db):
        assert row["url"] is None
        assert row["stripe_payment_link_id"] is None
        assert row["settlement_bank_account_id"] is None
        assert row["error"] is None
        assert row["created_at"] == row["updated_at"]


def test_sync_is_idempotent(db):
    sync_tracking(db)
    first_rows = list_tracking_rows(db)

    result = sync_tracking(db)

    assert result == {"inserted": 0, "pending": 0, "skipped": 0}
    assert list_tracking_rows(db) == first_rows


def test_sync_only_adds_new_history_rows(db):
    sync_tracking(db)
    db.execute(
        "INSERT INTO payment_status_history (id, invoice_id, old_status, new_status, changed_at) "
        "VALUES (8, 1003, 'open', 'overdue', '2026-08-25T00:05:00Z')"
    )

    result = sync_tracking(db)

    assert result == {"inserted": 1, "pending": 1, "skipped": 0}
    assert len(list_tracking_rows(db)) == 8


def test_sync_does_not_overwrite_existing_tracking_rows(db):
    sync_tracking(db)
    # Simulate a later processing step having moved the row on.
    db.execute(
        "UPDATE payment_link_tracking SET status = 'created' WHERE history_id = ?",
        (QUALIFYING_HISTORY_ID,),
    )

    sync_tracking(db)

    row = next(r for r in list_tracking_rows(db) if r["history_id"] == QUALIFYING_HISTORY_ID)
    assert row["status"] == "created"


def test_sync_does_not_modify_seeded_tables(db):
    def snapshot():
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            for table in ("payment_status_history", "invoices")
        }

    before = [list(map(tuple, rows)) for rows in snapshot().values()]
    sync_tracking(db)
    after = [list(map(tuple, rows)) for rows in snapshot().values()]

    assert before == after


# --- reset ----------------------------------------------------------------


def test_reset_then_sync_recreates_the_same_rows(db):
    sync_tracking(db)
    first = [(r["history_id"], r["status"], r["reason"]) for r in list_tracking_rows(db)]

    assert reset_tracking(db) == 7
    assert list_tracking_rows(db) == []

    assert sync_tracking(db) == {"inserted": 7, "pending": 1, "skipped": 6}
    second = [(r["history_id"], r["status"], r["reason"]) for r in list_tracking_rows(db)]
    assert second == first


def test_reset_keeps_seeded_history(db):
    sync_tracking(db)
    reset_tracking(db)

    count = db.execute("SELECT COUNT(*) FROM payment_status_history").fetchone()[0]
    assert count == 7
