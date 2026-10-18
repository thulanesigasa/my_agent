"""Synthetic supported listings and fake research providers; no live verification."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from config import settings
from core.store import store
from services import qualification as q, research_jobs as jobs, source_inspection
from services.contacts import save_contact, EligibilityError
from services.lead_service import (
    ingest_candidate,
    ensure_qualified,
    observation_fingerprint,
    draft_lead,
    review_lead,
)
from services.proposals import create_preview
from services.email_service import email_service
from agents.human_approval import approve_draft
from test_leads_phase4 import candidate, review_payload
from test_research_jobs import clear_wait

URL_A = "https://www.brabys.com/example-bakery"
URL_B = "https://www.sayellow.com/example-bakery"


def text(source="A", **changes):
    values = {
        "Business name": "Example Bakery",
        "Town": "Example Town",
        "Address": "1 Main Street, Example Town",
        "Phone": "+27100000000",
        "Email": "owner@example.test",
        "Business status": "active",
        "Activity verified": datetime.now(q.TZ).date().isoformat(),
        "Website": "none",
        **changes,
    }
    return f"Directory {source}\n" + "\n".join(f"{k}: {v}" for k, v in values.items())


def seed(permission=False):
    lead = ingest_candidate(candidate(source_url=URL_A))
    if permission:
        save_contact(
            "owner@example.test",
            verified=True,
            consent="granted",
            evidence="Explicit fixture recipient permission",
        )
    inspection = {
        "lead_id": lead["id"],
        "source_url": URL_A,
        "fingerprint": observation_fingerprint(lead),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "expires": time.time() + 86400,
        "findings": {"emails": [], "phones": [], "links": []},
        "qualification_fields": q.listing_fields(text()),
    }
    inspection = store.put("lead_inspections", lead["id"], inspection)
    work = {
        "source_url": URL_B,
        "search": {
            "query": "exact name town phone domain website",
            "urls": [URL_A, URL_B],
            "checked_at": inspection["checked_at"],
        },
        "fingerprint": q.digest(
            {"inspection": inspection, "observation": observation_fingerprint(lead)}
        ),
    }
    store.put("qualification_work", lead["id"], work)
    return lead, inspection, work


def publish(permission=False):
    lead, first, work = seed(permission)
    result = q.publish(lead, first, work, q.listing_fields(text("B")))
    return lead, first, result


def test_two_source_qualification_is_machine_attributed_and_never_grants_permission():
    lead, _, result = publish()
    assert result["decision"] == "qualified"
    reviewed = store.get("leads", lead["id"])
    assert reviewed["review"]["origin"] == "automation"
    contact = store.get("contacts", "owner@example.test")
    assert contact["verified"] and contact["consent"] == "unknown"
    with pytest.raises(EligibilityError, match="consent"):
        ensure_qualified(lead["id"])
    assert store.list("approvals") == store.list("messages") == []


def test_permission_allows_proposal_with_immutable_source_evidence():
    lead, _, result = publish(True)
    preview = create_preview(lead["id"], email_service.expected_email)
    approval = draft_lead(
        lead["id"],
        preview["subject"],
        preview["body"],
        email_service.expected_email,
        preview["id"],
    )
    evidence = approval["qualification_evidence"]
    assert evidence["id"] == result["evidence_id"]
    assert {s["url"] for s in evidence["sources"]} == {URL_A, URL_B}
    assert evidence["sources"][0]["snippets"]["activity verified"].startswith(
        "Activity verified:"
    )
    assert approval["status"] == "pending" and store.list("messages") == []


@pytest.mark.parametrize(
    "change",
    [
        {"Town": "Other Town"},
        {"Address": "99 Other Road"},
        {"Phone": "0110000000"},
        {"Email": "other@example.test"},
        {"Business name": "Other Bakery"},
    ],
)
def test_cross_source_disagreement_cannot_qualify(change):
    lead, first, work = seed()
    with pytest.raises(ValueError, match="disagree"):
        q.publish(lead, first, work, q.listing_fields(text("B", **change)))
    assert store.get("leads", lead["id"])["status"] != "qualified"
    assert store.get("contacts", "owner@example.test") is None


@pytest.mark.parametrize(
    "body",
    [
        "Example Bakery, Example Town. We are open. owner@example.test",
        text() + "\nEmail: other@example.test",
        text(
            **{
                "Activity verified": (
                    datetime.now(q.TZ).date() - timedelta(days=31)
                ).isoformat()
            }
        ),
        text(
            **{
                "Activity verified": (
                    datetime.now(q.TZ).date() + timedelta(days=1)
                ).isoformat()
            }
        ),
        text(**{"Phone": "+441234567890"}),
    ],
)
def test_bare_prose_repeated_fields_and_stale_or_future_activity_are_not_evidence(body):
    with pytest.raises(ValueError):
        q.listing_fields(body)


def test_identical_copied_sources_are_not_corroboration():
    lead, first, work = seed()
    with pytest.raises(ValueError, match="Identical"):
        q.publish(lead, first, work, q.listing_fields(text()))


@pytest.mark.parametrize(
    "changes,decision",
    [
        ({"Business status": "permanently closed"}, "excluded"),
        ({"Business status": "unknown"}, "needs_review"),
        ({"Website": "unknown"}, "needs_review"),
    ],
)
def test_closure_and_uncertain_status_do_not_qualify(changes, decision):
    lead, first, work = seed()
    if decision == "excluded":
        assert (
            q.publish(lead, first, work, q.listing_fields(text("B", **changes)))[
                "decision"
            ]
            == decision
        )
    else:
        with pytest.raises(ValueError):
            q.publish(lead, first, work, q.listing_fields(text("B", **changes)))
    assert store.get("leads", lead["id"])["status"] != "qualified"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hits",
    [
        [],
        [{"url": URL_A}] * 5,
        [{"url": "https://business.example.test/"}],
        [{"url": URL_A}],
        [{"url": "http://127.0.0.1/"}],
    ],
)
async def test_empty_capped_possible_site_same_domain_and_private_searches_remain_unqualified(
    monkeypatch, hits
):
    lead, _, _ = seed()
    monkeypatch.setattr(q, "reserve_request", lambda: None)
    monkeypatch.setattr(q, "request_search", AsyncMock(return_value={"results": hits}))
    result = await q.advance(lead, "qualify_search")
    assert result["decision"] == "needs_review"
    assert store.list("qualification_evidence") == []


@pytest.mark.asyncio
async def test_redirect_or_failed_corroboration_does_not_publish(monkeypatch):
    lead, _, _ = seed()
    monkeypatch.setattr(q, "reserve_request", lambda: None)
    monkeypatch.setattr(
        q,
        "request_provider",
        AsyncMock(
            return_value={
                "results": [
                    {"url": "https://other.example.test/", "raw_content": text("B")}
                ]
            }
        ),
    )
    result = await q.advance(lead, "qualify_extract")
    assert result["decision"] == "needs_review"


def test_operator_review_and_insufficient_budget_are_preserved():
    lead, _, _ = seed()
    assert q.start(lead, 1)["decision"] == "needs_review"
    reviewed = review_lead(lead["id"], review_payload(lead))
    assert q.start(reviewed, 5)["decision"] == "operator_review"
    assert store.get("leads", lead["id"]) == reviewed


@pytest.mark.asyncio
async def test_operator_review_during_job_takes_precedence(monkeypatch):
    lead, _, _ = seed()
    reviewed = review_lead(lead["id"], review_payload(lead))
    provider = AsyncMock(
        side_effect=AssertionError("Must not research over operator decision")
    )
    monkeypatch.setattr(q, "request_provider", provider)
    assert (await q.advance(reviewed, "qualify_extract"))[
        "decision"
    ] == "operator_review"
    provider.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["expire", "inspection", "negative"])
async def test_current_evidence_rechecked_at_approval_before_any_send(
    monkeypatch, change
):
    lead, first, result = publish(True)
    preview = create_preview(lead["id"], email_service.expected_email)
    approval = draft_lead(
        lead["id"],
        preview["subject"],
        preview["body"],
        email_service.expected_email,
        preview["id"],
    )
    if change == "expire":
        evidence = store.get("qualification_evidence", result["evidence_id"])
        store.put("qualification_evidence", evidence["id"], {**evidence, "expires": 0})
    elif change == "inspection":
        store.put(
            "lead_inspections",
            lead["id"],
            {**first, "qualification_fields": q.listing_fields(text("C"))},
        )
    else:
        q.result(store.get("leads", lead["id"]), "needs_review", "New website signal")
    send = AsyncMock(side_effect=AssertionError("Must not send"))
    monkeypatch.setattr(email_service, "send_email", send)
    with pytest.raises(EligibilityError):
        await approve_draft(approval["id"])
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_full_research_job_spends_four_bounded_requests_and_qualifies_without_sending(
    monkeypatch,
):
    lead = ingest_candidate(candidate(source_url=URL_A))
    monkeypatch.setattr(settings, "ALLOW_TAVILY_RESEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "fixture-only")
    monkeypatch.setattr(settings, "RESEARCH_JOBS_ENABLED", True)

    async def discover(**kwargs):
        q.reserve_request()
        return {"leads": [lead]}

    async def extract(operation, payload):
        url = payload["urls"][0]
        return {
            "results": [{"url": url, "raw_content": text("A" if url == URL_A else "B")}]
        }

    monkeypatch.setattr(jobs, "discover_web", discover)
    monkeypatch.setattr(source_inspection, "request_provider", extract)
    monkeypatch.setattr(q, "request_provider", extract)
    monkeypatch.setattr(
        q,
        "request_search",
        AsyncMock(return_value={"results": [{"url": URL_A}, {"url": URL_B}]}),
    )
    job = jobs.create_job(
        "Example Town", "bakery", limit=1, max_requests=4, auto_qualify=True
    )
    for _ in range(4):
        clear_wait(job["id"])
        assert await jobs.run_once()
    saved = store.get("research_jobs", job["id"])
    assert saved["status"] == "completed" and saved["requests_used"] == 4
    assert saved["results"][0]["bucket"] == "automatically_qualified"
    assert (
        saved["results"][0]["ready_to_draft"] is False
    )  # No invented recipient consent.
    assert store.get("leads", lead["id"])["review"]["origin"] == "automation"
    assert store.list("approvals") == store.list("messages") == []


def test_existing_optout_remains_suppressed_after_machine_contact_verification():
    lead, first, work = seed()
    save_contact(
        "owner@example.test", consent="unsubscribed", evidence="Actual recorded opt-out"
    )
    q.publish(lead, first, work, q.listing_fields(text("B")))
    assert store.get("contacts", "owner@example.test")["consent"] == "unsubscribed"
    with pytest.raises(EligibilityError, match="do-not-contact"):
        ensure_qualified(lead["id"])


def test_same_supported_domain_aliases_are_not_independent_and_suffix_attacks_are_unknown():
    assert q.canonical("https://www.brabys.com/branch") == q.canonical(
        "https://listings.brabys.com/branch"
    )
    assert q.canonical("https://brabys.com.evil.example/branch") is None
