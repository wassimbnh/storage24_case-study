"""Stand-in for Stripe's payment link API. No network calls."""

import logging
import uuid

logger = logging.getLogger(__name__)


def create_payment_link(
    *,
    invoice_id: int,
    amount_cents: int,
    currency: str,
    customer_email: str,
    stripe_customer_id: str | None,
    settlement_bank_account_id: int,
) -> dict:
    """Log the inputs and return a fake payment link as {"id", "url"}."""
    # Logged under the field names of the brief; stripeCustomerId stays None when absent.
    logger.info(
        "Stripe mock: create payment link %s",
        {
            "invoiceId": invoice_id,
            "amountCents": amount_cents,
            "currency": currency,
            "customerEmail": customer_email,
            "stripeCustomerId": stripe_customer_id,
            "settlementBankAccountId": settlement_bank_account_id,
        },
    )
    link_id = f"plink_mock_{uuid.uuid4().hex[:16]}"
    return {"id": link_id, "url": f"https://pay.stripe.mock/{link_id}"}
