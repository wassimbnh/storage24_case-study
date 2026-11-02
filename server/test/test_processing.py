import pytest

import stripe_mock
from database import list_tracking_rows, reset_tracking
from processing import process_pending
from sync import sync_tracking

QUALIFYING_HISTORY_ID = 4  # invoice 1002: open -> overdue


@pytest.fixture
def stripe_calls(monkeypatch):
    """Record every call to the Stripe mock while still returning its fake link."""
    calls = []
    real = stripe_mock.create_payment_link

    def recording(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(stripe_mock, "create_payment_link", recording)
    return calls


def tracking_row(db, history_id):
    return next(r for r in list_tracking_rows(db) if r["history_id"] == history_id)


def statuses(db):
    return [row["status"] for row in list_tracking_rows(db)]


# --- acceptance checks ----------------------------------------------------


def test_first_run_gives_6_skipped_and_1_created(db, stripe_calls):
    sync_tracking(db)

    result = process_pending(db)

    assert result == {"created": 1, "failed": 0, "skipped": 0, "not_claimed": 0}
    assert len(list_tracking_rows(db)) == 7
    assert statuses(db).count("skipped") == 6
    assert statuses(db).count("created") == 1


def test_created_row_is_invoice_1002_routed_to_account_2(db, stripe_calls):
    sync_tracking(db)
    process_pending(db)

    row = tracking_row(db, QUALIFYING_HISTORY_ID)
    assert row["invoice_id"] == 1002
    assert row["status"] == "created"
    assert row["settlement_bank_account_id"] == 2
    assert row["stripe_payment_link_id"].startswith("plink_mock_")
    assert row["url"].endswith(row["stripe_payment_link_id"])
    assert row["error"] is None


def test_running_again_creates_no_second_link(db, stripe_calls):
    sync_tracking(db)
    process_pending(db)
    first = tracking_row(db, QUALIFYING_HISTORY_ID)

    sync_tracking(db)
    result = process_pending(db)

    assert result == {"created": 0, "failed": 0, "skipped": 0, "not_claimed": 0}
    assert len(stripe_calls) == 1
    assert tracking_row(db, QUALIFYING_HISTORY_ID) == first


def test_reset_then_run_recreates_the_same_rows_once(db, stripe_calls):
    sync_tracking(db)
    process_pending(db)
    reset_tracking(db)

    sync_tracking(db)
    process_pending(db)

    assert len(list_tracking_rows(db)) == 7
    assert statuses(db).count("created") == 1
    assert len(stripe_calls) == 2  # one per run, never two in the same run


# --- Stripe inputs --------------------------------------------------------


def test_stripe_receives_invoice_and_routing_inputs(db, stripe_calls):
    sync_tracking(db)
    process_pending(db)

    assert stripe_calls == [
        {
            "invoice_id": 1002,
            "amount_cents": 24000,
            "currency": "EUR",
            "customer_email": "anna.keller@example.com",
            "stripe_customer_id": "cus_A1B2C3",
            "settlement_bank_account_id": 2,
        }
    ]


def test_null_stripe_customer_id_is_passed_through(db, stripe_calls):
    # Customer 101 has no Stripe customer; make their invoice qualify.
    db.execute("UPDATE invoices SET status = 'overdue' WHERE id = 1003")
    db.execute(
        "INSERT INTO payment_status_history (id, invoice_id, old_status, new_status, changed_at) "
        "VALUES (8, 1003, 'open', 'overdue', '2026-08-25T00:05:00Z')"
    )
    sync_tracking(db)
    process_pending(db)

    call = next(c for c in stripe_calls if c["invoice_id"] == 1003)
    assert call["stripe_customer_id"] is None
    assert tracking_row(db, 8)["status"] == "created"


# --- stale events ---------------------------------------------------------


def test_invoice_no_longer_overdue_is_skipped_as_stale(db, stripe_calls):
    sync_tracking(db)
    db.execute("UPDATE invoices SET status = 'paid' WHERE id = 1002")

    result = process_pending(db)

    assert result["skipped"] == 1
    row = tracking_row(db, QUALIFYING_HISTORY_ID)
    assert row["status"] == "skipped"
    assert "stale event" in row["reason"]
    assert "paid" in row["reason"]
    assert stripe_calls == []


# --- claim ----------------------------------------------------------------


def test_row_claimed_elsewhere_is_not_processed(db, stripe_calls):
    sync_tracking(db)
    db.execute(
        "UPDATE payment_link_tracking SET status = 'processing' WHERE history_id = ?",
        (QUALIFYING_HISTORY_ID,),
    )

    result = process_pending(db)

    assert result == {"created": 0, "failed": 0, "skipped": 0, "not_claimed": 0}
    assert stripe_calls == []
    assert tracking_row(db, QUALIFYING_HISTORY_ID)["status"] == "processing"


def test_lost_claim_race_does_not_call_stripe(db, stripe_calls, monkeypatch):
    import processing

    sync_tracking(db)
    real_transition = processing._transition

    def competing_run_claims_first(conn, tracking_id, from_status, to_status, **fields):
        if to_status == "processing":
            real_transition(conn, tracking_id, "pending", "processing")
        return real_transition(conn, tracking_id, from_status, to_status, **fields)

    monkeypatch.setattr(processing, "_transition", competing_run_claims_first)

    result = process_pending(db)

    assert result["not_claimed"] == 1
    assert stripe_calls == []


def test_row_is_processing_while_stripe_is_called(db, monkeypatch):
    sync_tracking(db)
    seen = []

    def check_claimed(**kwargs):
        seen.append(tracking_row(db, QUALIFYING_HISTORY_ID)["status"])
        return {"id": "plink_mock_test", "url": "https://pay.stripe.mock/plink_mock_test"}

    monkeypatch.setattr(stripe_mock, "create_payment_link", check_claimed)
    process_pending(db)

    assert seen == ["processing"]


# --- failures -------------------------------------------------------------


def test_routing_failure_marks_row_failed_with_error(db, stripe_calls):
    db.execute(
        "INSERT INTO bank_accounts (id, legal_entity_id, iban, bank_name, currency) "
        "VALUES (4, 2, 'DE00 0000 0000 0000000000', 'Second Bank', 'EUR')"
    )
    sync_tracking(db)

    result = process_pending(db)

    assert result["failed"] == 1
    row = tracking_row(db, QUALIFYING_HISTORY_ID)
    assert row["status"] == "failed"
    assert "refusing to guess" in row["error"]
    assert row["url"] is None
    assert row["stripe_payment_link_id"] is None
    assert stripe_calls == []


def test_stripe_failure_marks_row_failed_with_error(db, monkeypatch):
    def broken(**kwargs):
        raise RuntimeError("stripe unavailable")

    monkeypatch.setattr(stripe_mock, "create_payment_link", broken)
    sync_tracking(db)

    process_pending(db)

    row = tracking_row(db, QUALIFYING_HISTORY_ID)
    assert row["status"] == "failed"
    assert row["error"] == "stripe unavailable"


def test_failed_row_is_not_retried(db, monkeypatch, stripe_calls):
    db.execute(
        "INSERT INTO bank_accounts (id, legal_entity_id, iban, bank_name, currency) "
        "VALUES (4, 2, 'DE00 0000 0000 0000000000', 'Second Bank', 'EUR')"
    )
    sync_tracking(db)
    process_pending(db)

    result = process_pending(db)

    assert result == {"created": 0, "failed": 0, "skipped": 0, "not_claimed": 0}
    assert tracking_row(db, QUALIFYING_HISTORY_ID)["status"] == "failed"


def test_one_failure_does_not_block_other_rows(db, stripe_calls):
    # Second qualifying event (invoice 1003, Lyon) next to one that fails routing (1002).
    db.execute("UPDATE invoices SET status = 'overdue' WHERE id = 1003")
    db.execute(
        "INSERT INTO payment_status_history (id, invoice_id, old_status, new_status, changed_at) "
        "VALUES (8, 1003, 'open', 'overdue', '2026-08-25T00:05:00Z')"
    )
    db.execute(
        "INSERT INTO bank_accounts (id, legal_entity_id, iban, bank_name, currency) "
        "VALUES (4, 2, 'DE00 0000 0000 0000000000', 'Second Bank', 'EUR')"
    )
    sync_tracking(db)

    result = process_pending(db)

    assert result == {"created": 1, "failed": 1, "skipped": 0, "not_claimed": 0}
    assert tracking_row(db, QUALIFYING_HISTORY_ID)["status"] == "failed"
    created = tracking_row(db, 8)
    assert created["status"] == "created"
    assert created["settlement_bank_account_id"] == 3


def test_skipped_rows_from_sync_are_left_untouched(db, stripe_calls):
    sync_tracking(db)
    before = [r for r in list_tracking_rows(db) if r["status"] == "skipped"]

    process_pending(db)

    after = [r for r in list_tracking_rows(db) if r["history_id"] != QUALIFYING_HISTORY_ID]
    assert after == before
