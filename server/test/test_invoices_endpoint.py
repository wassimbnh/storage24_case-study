def test_invoices_endpoint_returns_seeded_invoices_with_customer_name(client):
    response = client.get("/invoices")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1001, "customer_name": "Anna Keller", "status": "paid",
         "amount_cents": 15000, "currency": "EUR", "due_date": "2026-06-15"},
        {"id": 1002, "customer_name": "Anna Keller", "status": "overdue",
         "amount_cents": 24000, "currency": "EUR", "due_date": "2026-07-15"},
        {"id": 1003, "customer_name": "Marc Petit", "status": "open",
         "amount_cents": 18000, "currency": "EUR", "due_date": "2026-08-24"},
        {"id": 1004, "customer_name": "Julia Wagner", "status": "void",
         "amount_cents": 9800, "currency": "EUR", "due_date": "2026-06-03"},
    ]


def test_invoices_endpoint_is_read_only(client):
    client.get("/invoices")

    assert client.get("/tracking").json() == []
