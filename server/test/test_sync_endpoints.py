def test_tracking_is_empty_at_startup(client):
    response = client.get("/tracking")

    assert response.status_code == 200
    assert response.json() == []


def test_sync_endpoint_returns_counts(client):
    response = client.post("/sync")

    assert response.status_code == 200
    assert response.json() == {"inserted": 7, "pending": 1, "skipped": 6}


def test_tracking_endpoint_returns_synced_rows(client):
    client.post("/sync")

    rows = client.get("/tracking").json()

    assert len(rows) == 7
    assert {row["status"] for row in rows} == {"pending", "skipped"}
    expected_columns = {
        "id", "history_id", "invoice_id", "status", "reason", "error", "url",
        "stripe_payment_link_id", "settlement_bank_account_id", "created_at", "updated_at",
    }
    assert set(rows[0]) == expected_columns


def test_second_sync_adds_nothing(client):
    client.post("/sync")

    assert client.post("/sync").json() == {"inserted": 0, "pending": 0, "skipped": 0}
    assert len(client.get("/tracking").json()) == 7


def test_reset_endpoint_clears_tracking_and_allows_rerun(client):
    client.post("/sync")

    response = client.post("/reset")

    assert response.status_code == 200
    assert response.json() == {"deleted": 7}
    assert client.get("/tracking").json() == []
    assert client.post("/sync").json() == {"inserted": 7, "pending": 1, "skipped": 6}


def test_reset_on_empty_table_deletes_nothing(client):
    assert client.post("/reset").json() == {"deleted": 0}
