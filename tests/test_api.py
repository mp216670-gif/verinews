def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_end_to_end_article_verification_lifecycle(client):
    # 1. Register admin user
    res_admin = client.post(
        "/api/v1/auth/register",
        json={"username": "alice_admin", "email": "alice@example.com", "password": "AdminPassword123!"},
    )
    assert res_admin.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "alice_admin", "password": "AdminPassword123!"},
    ).json()
    admin_token = admin_login["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Register reporter user
    res_reporter = client.post(
        "/api/v1/auth/register",
        json={
            "username": "bob_reporter",
            "email": "bob@example.com",
            "password": "ReporterPassword123!",
            "role": "reporter",
        },
    )
    assert res_reporter.status_code == 201

    reporter_login = client.post(
        "/api/v1/auth/login",
        json={"username": "bob_reporter", "password": "ReporterPassword123!"},
    ).json()
    reporter_token = reporter_login["access_token"]
    reporter_headers = {"Authorization": f"Bearer {reporter_token}"}

    # 3. Reporter submits article
    art_payload = {
        "title": "Clean Energy Infrastructure Reaches 60% Adoption in Regional Grid",
        "content": (
            "Regional utility authorities confirmed in a press release that renewable generation supplied "
            "60% of total electrical demand over the previous quarter. "
            "According to the official statement from Reuters Energy Desk, wind and solar arrays contributed "
            "the largest single share. Directors noted: 'Grid stability remained consistent throughout the peak demand cycle.'"
        ),
        "publisher": "Reuters",
        "author": "Marcus Vance",
        "source_url": "https://reuters.com/business/clean-energy-grid-report",
    }
    submit_res = client.post("/api/v1/articles", json=art_payload, headers=reporter_headers)
    assert submit_res.status_code == 201
    article_id = submit_res.json()["id"]

    # 4. Reader tries to get pending article (should be forbidden or not found)
    reader_res = client.get(f"/api/v1/articles/{article_id}")
    assert reader_res.status_code == 403

    # 5. Reporter triggers verification
    verify_res = client.post(
        f"/api/v1/articles/{article_id}/verify",
        json={"provider_name": "hybrid"},
        headers=reporter_headers,
    )
    assert verify_res.status_code == 200
    report_data = verify_res.json()
    assert report_data["claims_count"] >= 1

    # 6. Retrieve trust score
    score_res = client.get(f"/api/v1/articles/{article_id}/trust-score", headers=reporter_headers)
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert score_data["overall_score"] >= 60.0
    assert "explanation" in score_data

    # 7. Reporter calibrates / reviews score with an adjustment
    review_res = client.post(
        f"/api/v1/articles/{article_id}/review",
        json={
            "decision": "approved",
            "score_adjustment": 5.0,
            "notes": "Verified source documents and validated regional utility telemetry data.",
        },
        headers=reporter_headers,
    )
    assert review_res.status_code == 200
    updated_score = review_res.json()
    assert updated_score["reviewer_adjustment"] == 5.0

    # 8. Now reader can view article in public feed
    public_articles = client.get("/api/v1/articles").json()
    assert public_articles["total"] >= 1
    found = any(a["id"] == article_id for a in public_articles["articles"])
    assert found is True

    # 9. Admin checks platform metrics
    metrics_res = client.get("/api/v1/admin/metrics", headers=admin_headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["articles"]["total"] >= 1
    assert metrics["users"]["total"] >= 2
    assert metrics["verifications"]["total_reports"] >= 1


def test_instant_verification_public_no_auth(client):
    # Public general user with no token checks a suspicious proposition
    res = client.post(
        "/api/v1/articles/verify-instant",
        json={
            "title": "Shocking truth revealed: Drinking lemon tea cures all illnesses guaranteed 100%",
            "content": "Secret doctors tricks revealed that lemon cures everything guaranteed 100% without medication.",
            "publisher": "Viral Gossip Blog",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["article_id"] > 0
    assert "Disputed" in data["provider_verdict"] or "Questionable" in data["provider_verdict"]
    assert data["grade"] in ("C", "D")
    assert len(data["claims"]) >= 1
    assert "explanation" in data
