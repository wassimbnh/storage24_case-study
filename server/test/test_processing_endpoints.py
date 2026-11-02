def test_process_endpoint_after_sync(client):
    client.post("/sync")

    response = client.post("/process")

    assert response.status_code == 200
    assert response.json() == {"created": 1, "failed": 0, "skipped": 0, "not_claimed": 0}


def test_run_endpoint_matches_acceptance_checks(client):
    response = client.post("/run")

    assert response.status_code == 200
    assert response.json() == {
        "sync": {"inserted": 7, "pending": 1, "skipped": 6},
        "process": {"created": 1, "failed": 0, "skipped": 0, "not_claimed": 0},
    }
    rows = client.get("/tracking").json()
    created = [r for r in rows if r["status"] == "created"]
    assert len(rows) == 7
    assert [(r["invoice_id"], r["settlement_bank_account_id"]) for r in created] == [(1002, 2)]


def test_second_run_adds_nothing(client):
    client.post("/run")
    link_id = next(r for r in client.get("/tracking").json() if r["status"] == "created")[
        "stripe_payment_link_id"
    ]

    response = client.post("/run")

    assert response.json() == {
        "sync": {"inserted": 0, "pending": 0, "skipped": 0},
        "process": {"created": 0, "failed": 0, "skipped": 0, "not_claimed": 0},
    }
    rows = client.get("/tracking").json()
    assert [r["stripe_payment_link_id"] for r in rows if r["status"] == "created"] == [link_id]


def test_reset_then_run_recreates_rows(client):
    client.post("/run")
    client.post("/reset")

    response = client.post("/run")

    assert response.json()["sync"]["inserted"] == 7
    assert response.json()["process"]["created"] == 1
    assert len(client.get("/tracking").json()) == 7
