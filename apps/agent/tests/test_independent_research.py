"""Independent provenance survives import without becoming permission or verification."""

import pytest
from fastapi.testclient import TestClient
from core.store import store
from services.lead_service import ingest_candidate, lead_view
from test_leads_phase4 import candidate, qualified


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def test_manual_provenance_is_durable_but_not_qualification_or_consent(api):
    data = {k: v for k, v in candidate().items() if k != "source"}
    result = api.post(
        "/api/leads",
        json={
            **data,
            "source_kind": "public_business_social",
            "source_note": "Original business profile, checked branch address",
        },
    )
    assert result.status_code == 200
    lead = result.json()
    assert lead["observation"]["source_kind"] == "public_business_social"
    assert (
        lead["observations"][0]["source_note"]
        == "Original business profile, checked branch address"
    )
    assert lead["status"] == "needs_review" and not lead["ready_to_draft"]
    assert store.list("contacts") == [] and store.list("approvals") == []
    assert (
        api.get("/api/leads").json()["leads"][0]["observation"] == lead["observation"]
    )


def test_csv_provenance_validated_for_all_rows_before_writes(api):
    header = "name,location,source_url,source_kind,source_note\n"
    good = "Bakery,Example Town,https://business.example.test,business_owned_page,Original branch page\n"
    bad = "Shop,Example Town,https://shop.example.test,owner_provided,\n"
    assert (
        api.post(
            "/api/leads/import", json={"csv_text": header + good + bad}
        ).status_code
        == 400
    )
    assert store.list("leads") == []
    result = api.post("/api/leads/import", json={"csv_text": header + good})
    assert result.status_code == 200 and result.json()["unique_leads"] == 1
    assert store.list("leads")[0]["observation"]["source_kind"] == "business_owned_page"
    assert store.list("contacts") == []


def test_unknown_provenance_kind_rejected_and_legacy_csv_still_works(api):
    data = {k: v for k, v in candidate().items() if k != "source"}
    assert (
        api.post("/api/leads", json={**data, "source_kind": "invented"}).status_code
        == 422
    )
    result = api.post(
        "/api/leads/import",
        json={
            "csv_text": "name,location,source_url\nBakery,Example Town,https://business.example.test\n"
        },
    )
    assert result.status_code == 200
    lead = store.list("leads")[0]
    assert (
        lead["observation"]["source_kind"] == ""
        and not lead_view(lead)["ready_to_draft"]
    )


def test_changing_provenance_invalidates_review_and_preserves_prior_note():
    lead = qualified()
    again = ingest_candidate(
        candidate(
            source_kind="owner_provided", source_note="New owner supplied these details"
        )
    )
    assert again["id"] == lead["id"]
    assert again["review_invalidated"] and again["status"] == "needs_review"
    assert again["review"] == lead["review"]
    assert (
        again["observations"][-1]["source_note"] == "New owner supplied these details"
    )
    assert not lead_view(again)["ready_to_draft"]
