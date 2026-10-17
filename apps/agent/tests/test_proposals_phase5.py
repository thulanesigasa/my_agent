"""Portfolio proposals use reviewed records and local configuration, without providers."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import settings
from core.store import store, StateStore, ConflictError
from services.contacts import EligibilityError, save_contact
from services.email_service import email_service
from services.lead_service import draft_lead, ingest_candidate, review_lead
from services.proposals import (
    Portfolio,
    portfolio,
    save_portfolio,
    match_projects,
    create_preview,
)
from test_leads_phase4 import qualified, candidate, review_payload


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def test_seed_uses_only_supplied_projects_and_no_inferred_features():
    catalog = portfolio()
    assert catalog["portfolio_url"] == "https://ts-industries.co.za/"
    assert [p["url"] for p in catalog["projects"]] == [
        "https://rbptech.co.za/",
        "https://rhymamusic.co.za/",
    ]
    assert all(not p["description"] and not p["tags"] for p in catalog["projects"])
    assert catalog["version"] == 0


def test_fallback_and_configured_industry_matching_are_explained():
    catalog = portfolio()
    assert all(
        "General portfolio example" in p["reason"]
        for p in match_projects({"industry": "bakery"}, catalog)
    )
    catalog["projects"][1]["tags"] = ["music", "artist"]
    matches = match_projects({"industry": "music artist"}, catalog)
    assert [p["id"] for p in matches] == ["rhyma-music"]
    assert matches[0]["reason"] == "Configured industry tags: music, artist"
    # A tag does not match inside a different word; inactive examples cannot be selected.
    assert len(match_projects({"industry": "musical instruments"}, catalog)) == 2
    catalog["projects"][1]["active"] = False
    assert [p["id"] for p in match_projects({"industry": "music"}, catalog)] == [
        "rbp-tech"
    ]


def test_catalog_updates_persist_and_concurrent_editor_is_rejected():
    payload = Portfolio(**portfolio())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: save_or_conflict(payload), range(2)))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert sum(isinstance(r, ConflictError) for r in results) == 1
    assert StateStore(store.path).get("portfolio", "current")["catalog"]["version"] == 1


def save_or_conflict(payload):
    try:
        return save_portfolio(payload)
    except ConflictError as exc:
        return exc


@pytest.mark.parametrize(
    "change",
    [
        {"agency_name": "\r\nInjected"},
        {"agency_name": " "},
        {"portfolio_url": "javascript:bad"},
        {"portfolio_url": "http://127.0.0.1/"},
        {
            "projects": [
                {
                    "id": "bad",
                    "name": "Example",
                    "url": "https://user:secret@example.test/",
                }
            ]
        },
        {
            "projects": [
                {
                    "id": "bad",
                    "name": "Example",
                    "url": "https://example.test/",
                    "tags": ["x" * 61],
                }
            ]
        },
    ],
    ids=[
        "header-injection",
        "blank-agency",
        "script-url",
        "local-url",
        "credential-url",
        "long-tag",
    ],
)
def test_catalog_rejects_unsafe_or_invalid_fields(change):
    with pytest.raises(ValidationError):
        Portfolio(**{**portfolio(), **change})


def test_duplicate_project_ids_and_unknown_fields_are_rejected():
    catalog = portfolio()
    catalog["projects"].append(catalog["projects"][0])
    with pytest.raises(ValidationError):
        Portfolio(**catalog)
    with pytest.raises(ValidationError):
        Portfolio(**{**portfolio(), "model_api_key": "no"})


def test_preview_contains_links_identity_scope_signature_and_optout():
    lead = qualified()
    preview = create_preview(lead["id"], email_service.expected_email)
    for text in [
        "Example Bakery",
        "Example Town",
        "https://ts-industries.co.za/",
        "https://rbptech.co.za/",
        "https://rhymamusic.co.za/",
        "pharezsigasa@gmail.com",
        "+447544357979",
        "unsubscribe",
        "understand the scope",
        "couldn't find",
    ]:
        assert text in preview["body"]
    for unsupported in ["free 30-minute", "guaranteed", "SEO", "R500"]:
        assert unsupported not in preview["body"]
    assert store.list("approvals") == store.list("messages") == []


def test_no_active_projects_still_uses_agency_portfolio():
    catalog = portfolio()
    for project in catalog["projects"]:
        project["active"] = False
    save_portfolio(Portfolio(**catalog))
    preview = create_preview(qualified()["id"], email_service.expected_email)
    assert preview["projects"] == []
    assert "https://ts-industries.co.za/" in preview["body"]
    assert "projects we've developed" not in preview["body"]


@pytest.mark.parametrize(
    "condition",
    [
        "unreviewed",
        "no-permission",
        "unsubscribed",
        "stale",
        "website-found",
        "no-mailbox",
    ],
)
def test_proposal_cannot_bypass_existing_qualification(condition):
    if condition == "unreviewed":
        lead = ingest_candidate(candidate())
    else:
        lead = qualified(consent=condition != "no-permission")
    if condition == "unsubscribed":
        save_contact("owner@example.test", consent="unsubscribed", evidence="Stop")
    if condition == "stale":
        store.put(
            "leads",
            lead["id"],
            {
                **lead,
                "review": {
                    **lead["review"],
                    "reviewed_at": (
                        datetime.now(timezone.utc) - timedelta(days=31)
                    ).isoformat(),
                },
            },
        )
    if condition == "website-found":
        review_lead(
            lead["id"],
            review_payload(
                lead,
                decision="rejected",
                decision_note="Existing business website confirmed",
                website_status="found",
                website_url="https://bakery.example.test/",
            ),
        )
    with pytest.raises(EligibilityError):
        create_preview(
            lead["id"],
            "" if condition == "no-mailbox" else email_service.expected_email,
        )
    assert store.list("proposal_previews") == store.list("approvals") == []


def test_operator_edits_and_source_snapshot_survive_duplicate_queue_attempt():
    lead = qualified()
    preview = create_preview(lead["id"], email_service.expected_email)
    first = draft_lead(
        lead["id"],
        "Edited subject",
        "Edited body",
        email_service.expected_email,
        preview["id"],
    )
    assert (
        first["subject"] == "Edited subject"
        and first["draft_response"] == "Edited body"
    )
    assert first["proposal_snapshot"]["edited_before_queue"]
    second = draft_lead(
        lead["id"],
        preview["subject"],
        preview["body"],
        email_service.expected_email,
        preview["id"],
    )
    assert second == first
    catalog = portfolio()
    catalog["projects"] = []
    save_portfolio(Portfolio(**catalog))
    assert (
        len(store.get("approvals", first["id"])["proposal_snapshot"]["projects"]) == 2
    )


@pytest.mark.parametrize(
    "condition", ["review", "portfolio", "mailbox", "other-lead", "missing-preview"]
)
def test_stale_or_wrong_preview_cannot_be_queued(condition):
    lead = qualified()
    preview = create_preview(lead["id"], email_service.expected_email)
    mailbox, preview_id = email_service.expected_email, preview["id"]
    if condition == "review":
        review_lead(lead["id"], review_payload(lead))
    if condition == "portfolio":
        save_portfolio(Portfolio(**portfolio()))
    if condition == "mailbox":
        mailbox = "other@example.test"
    if condition == "other-lead":
        other = ingest_candidate(candidate(name="Second Bakery", address="2 Street"))
        lead = review_lead(other["id"], review_payload(other))
    if condition == "missing-preview":
        preview_id = "missing"
    with pytest.raises(ValueError):
        draft_lead(lead["id"], preview["subject"], preview["body"], mailbox, preview_id)
    assert store.list("approvals") == []


def test_api_auth_preview_generation_editing_and_conflicts(api, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.get("/api/portfolio").status_code == 401
    assert api.put("/api/portfolio", json=portfolio()).status_code == 401
    lead = qualified()
    assert api.post(f"/api/leads/{lead['id']}/proposal").status_code == 401
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    catalog = api.get("/api/portfolio").json()
    assert api.put("/api/portfolio", json=catalog).status_code == 200
    assert api.put("/api/portfolio", json=catalog).status_code == 409
    preview = api.post(f"/api/leads/{lead['id']}/proposal").json()
    response = api.post(
        f"/api/leads/{lead['id']}/draft",
        json={
            "subject": preview["subject"],
            "body": "My edited proposal",
            "proposal_preview_id": preview["id"],
        },
    )
    assert response.status_code == 200
    assert response.json()["proposal_snapshot"]["id"] == preview["id"]
    assert api.post("/api/leads/missing/proposal").status_code == 403


@pytest.mark.asyncio
async def test_core_composition_uses_local_catalog_without_models_or_memory(
    monkeypatch,
):
    from services.llm_factory import llm_factory
    from core.memory import memory_manager
    from agents.outreach_agent import compose_pitch_node, outreach_dispatcher_node

    model = AsyncMock(side_effect=AssertionError("No model calls"))
    memory = AsyncMock(side_effect=AssertionError("No memory provider calls"))
    monkeypatch.setattr(llm_factory, "invoke_drafter", model)
    monkeypatch.setattr(memory_manager, "search_memory", memory)
    lead = qualified()
    result = await compose_pitch_node({"enriched_leads": [lead]})
    assert len(result["drafted_pitches"]) == 1
    await outreach_dispatcher_node(result)
    approval = store.list("approvals")[0]
    assert (
        approval["proposal_snapshot"]["portfolio_url"] == "https://ts-industries.co.za/"
    )
    assert approval["status"] == "pending" and store.list("messages") == []
    model.assert_not_awaited()
    memory.assert_not_awaited()


@pytest.mark.asyncio
async def test_generated_proposal_sends_only_exact_approved_edit_once(monkeypatch):
    import base64
    from email import message_from_bytes, policy
    from agents.human_approval import approve_draft
    from test_foundation import gmail_client

    lead = qualified()
    preview = create_preview(lead["id"], email_service.expected_email)
    edited = preview["body"] + "\nA final operator note."
    approval = draft_lead(
        lead["id"],
        preview["subject"],
        edited,
        email_service.expected_email,
        preview["id"],
    )
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    assert messages.send.call_count == 0
    await approve_draft(approval["id"])
    await approve_draft(approval["id"])
    assert messages.send.call_count == 1
    raw = messages.send.call_args.kwargs["body"]["raw"]
    message = message_from_bytes(base64.urlsafe_b64decode(raw), policy=policy.default)
    assert message["Subject"] == preview["subject"]
    assert message.get_body(preferencelist=("plain",)).get_content().strip() == edited
    assert store.get("approvals", approval["id"])["status"] == "sent"


def test_business_name_cannot_inject_a_subject_header():
    lead = ingest_candidate(candidate(name="Example\r\nBcc: injected@example.test"))
    save_contact(
        "owner@example.test",
        verified=True,
        consent="granted",
        evidence="Fixture permission",
    )
    lead = review_lead(lead["id"], review_payload(lead))
    preview = create_preview(lead["id"], email_service.expected_email)
    assert "\n" not in preview["subject"] and "\r" not in preview["subject"]
