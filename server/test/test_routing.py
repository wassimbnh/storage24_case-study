import pytest

from routing import RoutingError, resolve_settlement_bank_account


def test_invoice_1002_routes_to_munich_south_account(db):
    assert resolve_settlement_bank_account(db, 1002) == 2


def test_routing_follows_the_park_not_the_customer(db):
    # Customer 100 has invoices at parks of two different legal entities.
    assert resolve_settlement_bank_account(db, 1001) == 1  # park 10 -> entity 1
    assert resolve_settlement_bank_account(db, 1002) == 2  # park 11 -> entity 2


def test_french_park_routes_to_french_account(db):
    assert resolve_settlement_bank_account(db, 1003) == 3


def test_unknown_invoice_fails(db):
    with pytest.raises(RoutingError, match="invoice 9999 not found"):
        resolve_settlement_bank_account(db, 9999)


def test_no_account_in_invoice_currency_fails(db):
    db.execute(
        "INSERT INTO invoices (id, customer_id, park_id, amount_cents, currency, status, created_at, due_date) "
        "VALUES (2001, 100, 11, 5000, 'CHF', 'overdue', '2026-07-01', '2026-07-15')"
    )

    with pytest.raises(RoutingError, match="no CHF bank account for legal entity 2"):
        resolve_settlement_bank_account(db, 2001)


def test_multiple_matching_accounts_fails_instead_of_guessing(db):
    db.execute(
        "INSERT INTO bank_accounts (id, legal_entity_id, iban, bank_name, currency) "
        "VALUES (4, 2, 'DE00 0000 0000 0000000000', 'Second Bank', 'EUR')"
    )

    with pytest.raises(RoutingError, match=r"2 EUR bank accounts for legal entity 2 \(ids 2, 4\)"):
        resolve_settlement_bank_account(db, 1002)


def test_account_in_other_currency_is_ignored(db):
    db.execute(
        "INSERT INTO bank_accounts (id, legal_entity_id, iban, bank_name, currency) "
        "VALUES (4, 2, 'CH00 0000 0000 0000 0000 0', 'Swiss Bank', 'CHF')"
    )

    assert resolve_settlement_bank_account(db, 1002) == 2
