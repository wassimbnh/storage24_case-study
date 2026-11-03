def invoices_by_id(client):
    return {invoice["id"]: invoice for invoice in client.get("/invoices").json()}


def test_invoices_endpoint_returns_seeded_invoices_with_customer_name(client):
    response = client.get("/invoices")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1001, "customer_name": "Anna Keller", "status": "paid",
         "amount_cents": 15000, "currency": "EUR", "due_date": "2026-06-15", "payment_link": None, "no_link_reason": None},
        {"id": 1002, "customer_name": "Anna Keller", "status": "overdue",
         "amount_cents": 24000, "currency": "EUR", "due_date": "2026-07-15", "payment_link": None, "no_link_reason": None},
        {"id": 1003, "customer_name": "Marc Petit", "status": "open",
         "amount_cents": 18000, "currency": "EUR", "due_date": "2026-08-24", "payment_link": None, "no_link_reason": None},
        {"id": 1004, "customer_name": "Julia Wagner", "status": "void",
         "amount_cents": 9800, "currency": "EUR", "due_date": "2026-06-03", "payment_link": None, "no_link_reason": None},
    ]


def test_invoices_endpoint_is_read_only(client):
    client.get("/invoices")

    assert client.get("/tracking").json() == []


def test_after_run_only_invoice_1002_has_a_payment_link(client):
    client.post("/run")

    invoices = invoices_by_id(client)

    assert [i for i, invoice in invoices.items() if invoice["payment_link"]] == [1002]


def test_payment_link_shows_generated_link_and_routed_account(client):
    client.post("/run")
    tracking = next(r for r in client.get("/tracking").json() if r["status"] == "created")

    link = invoices_by_id(client)[1002]["payment_link"]

    assert link["id"] == tracking["stripe_payment_link_id"]
    assert link["url"] == tracking["url"]
    assert link["history_id"] == 4
    assert link["park"] == {"name": "Storage24 München Süd", "city": "Munich"}
    assert link["bank_account"] == {
        "id": 2, "bank_name": "Commerzbank", "iban": "DE44 7002 0270 0009876543",
        "currency": "EUR", "legal_entity": {"id": 2, "name": "Storage24 München Süd GmbH"},
    }


def test_payment_link_disappears_after_reset(client):
    client.post("/run")
    client.post("/reset")

    assert all(invoice["payment_link"] is None for invoice in client.get("/invoices").json())


def test_invoices_without_link_show_the_skip_reason_of_their_latest_event(client):
    client.post("/run")

    invoices = invoices_by_id(client)

    assert invoices[1001]["no_link_reason"] == "transition open -> paid is not open -> overdue"
    assert invoices[1002]["no_link_reason"] is None
    assert invoices[1003]["no_link_reason"] == "transition NULL -> open is not open -> overdue"
    assert invoices[1004]["no_link_reason"] == "transition open -> void is not open -> overdue"
