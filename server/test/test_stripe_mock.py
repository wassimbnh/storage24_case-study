import logging

from stripe_mock import create_payment_link

INPUTS = dict(
    invoice_id=1002,
    amount_cents=24000,
    currency="EUR",
    customer_email="customer@example.com",
    stripe_customer_id=None,
    settlement_bank_account_id=2,
)


def test_returns_fake_link_id_and_url():
    link = create_payment_link(**INPUTS)

    assert link["id"].startswith("plink_mock_")
    assert link["url"].endswith(link["id"])
    assert ".mock/" in link["url"]


def test_each_call_returns_a_new_link_id():
    assert create_payment_link(**INPUTS)["id"] != create_payment_link(**INPUTS)["id"]


def test_logs_inputs_with_brief_field_names(caplog):
    with caplog.at_level(logging.INFO, logger="stripe_mock"):
        create_payment_link(**INPUTS)

    message = caplog.records[-1].getMessage()
    for expected in (
        "'invoiceId': 1002",
        "'amountCents': 24000",
        "'currency': 'EUR'",
        "'customerEmail': 'customer@example.com'",
        "'stripeCustomerId': None",  # null passed through unchanged
        "'settlementBankAccountId': 2",
    ):
        assert expected in message
