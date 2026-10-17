"""Offline evidence, budget, deduplication and dispatch-boundary regressions."""

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi.testclient import TestClient
from core.store import store, ConflictError, StateStore
from config import settings
from services.contacts import save_contact, EligibilityError
from services.email_service import email_service
from agents.human_approval import approve_draft
from services.lead_service import (
    ingest_candidate,
    review_lead,
    ensure_qualified,
    lead_view,
    draft_lead,
    public_url,
)
from services import lead_discovery
from routers.leads import ReviewInput
from test_foundation import gmail_client


def candidate(**changes):
    return {
        "name": "Example Bakery",
        "location": "Example Town",
        "address": "1 Main Street",
        "phone": "010 000 0000",
        "email": "owner@example.test",
        "website": "",
        "industry": "bakery",
        "source": "manual",
        "source_url": "https://directory.example.test/bakery",
        **changes,
    }


def review_payload(lead, **changes):
    return ReviewInput(
        **{
            "revision": lead.get("revision", 0),
            "identity_verified": True,
            "identity_source": lead["source_url"],
            "identity_note": "Branch address and current activity confirmed",
            "business_status": "active",
            "website_status": "not_found_after_review",
            "website_source": "https://search.example.test/?q=example-bakery",
            "website_note": "Checked exact name/town, directory and current social profile; no independent site found",
            "contact_verified": True,
            "email": "owner@example.test",
            "contact_source": lead["source_url"],
            "contact_note": "Exact business email listed on this branch page",
            "decision": "qualified",
            **changes,
        }
    ).model_dump()


def qualified(consent=True):
    lead = ingest_candidate(candidate())
    if consent:
        save_contact(
            "owner@example.test",
            verified=True,
            consent="granted",
            evidence="Explicit fixture permission",
        )
    return review_lead(lead["id"], review_payload(lead))


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def test_imports_are_unverified_candidates_and_never_grant_consent():
    lead = ingest_candidate(candidate())
    assert lead["missing_website"] is None
    assert lead["requires_review"] and lead["status"] == "needs_review"
    assert store.list("contacts") == []
    assert not lead_view(lead)["ready_to_draft"]
    with pytest.raises(EligibilityError):
        ensure_qualified(lead["id"])


def test_complete_review_qualifies_evidence_but_does_not_create_permission():
    lead = qualified(consent=False)
    contact = store.get("contacts", "owner@example.test")
    assert contact["verified"] and contact["consent"] == "unknown"
    assert ensure_qualified(lead["id"], require_consent=False)
    with pytest.raises(EligibilityError):
        draft_lead(lead["id"], "Website", "Hello", email_service.expected_email)


@pytest.mark.parametrize(
    "change",
    [
        {"identity_verified": False},
        {"business_status": "unknown"},
        {"business_status": "inactive"},
        {"website_status": "uncertain"},
        {"website_status": "not_checked"},
        {"contact_verified": False},
        {"identity_note": " "},
        {"website_source": ""},
        {"contact_note": ""},
        {"email": ""},
    ],
)
def test_incomplete_or_uncertain_evidence_cannot_qualify(change):
    lead = ingest_candidate(candidate())
    with pytest.raises(ValueError):
        review_lead(lead["id"], review_payload(lead, **change))


def test_existing_website_and_conflicting_no_website_fields_cannot_qualify():
    lead = ingest_candidate(candidate())
    with pytest.raises(ValueError):
        review_lead(
            lead["id"],
            review_payload(
                lead, website_status="found", website_url="https://bakery.example.test"
            ),
        )
    with pytest.raises(ValueError, match="conflicts"):
        review_lead(
            lead["id"], review_payload(lead, website_url="https://bakery.example.test")
        )


def test_review_preserves_suppression_and_does_not_grant_consent():
    lead = ingest_candidate(candidate())
    save_contact("owner@example.test", consent="unsubscribed", evidence="Asked to stop")
    review_lead(lead["id"], review_payload(lead))
    assert store.get("contacts", "owner@example.test")["consent"] == "unsubscribed"
    assert not lead_view(store.get("leads", lead["id"]))["ready_to_draft"]


def test_reimport_same_candidate_preserves_review_and_changed_source_invalidates_it():
    lead = qualified()
    identical = ingest_candidate(candidate())
    assert identical["id"] == lead["id"]
    assert identical["review"] == lead["review"]
    assert ensure_qualified(lead["id"])
    changed = ingest_candidate(candidate(website="https://bakery.example.test"))
    assert changed["status"] == "needs_review" and changed["review_invalidated"]
    assert len(changed["observations"]) == 2
    assert changed["review"] == lead["review"]
    with pytest.raises(EligibilityError):
        ensure_qualified(lead["id"])


def test_same_name_branches_are_not_merged_and_are_flagged_for_review():
    one = ingest_candidate(candidate())
    two = ingest_candidate(candidate(address="2 Side Street", phone="010 000 0001"))
    assert one["id"] != two["id"]
    assert lead_view(one)["possible_duplicates"] == [two["id"]]


def test_stale_or_concurrently_changed_evidence_blocks_dispatch_and_review():
    lead = qualified()
    with pytest.raises(ConflictError):
        review_lead(lead["id"], review_payload(lead, revision=0))
    old = {
        **lead["review"],
        "reviewed_at": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
    }
    store.put("leads", lead["id"], {**lead, "review": old})
    with pytest.raises(EligibilityError, match="30 days"):
        ensure_qualified(lead["id"])


def test_atomic_reimport_deduplicates_concurrent_records():
    with ThreadPoolExecutor(max_workers=4) as workers:
        values = list(workers.map(lambda _: ingest_candidate(candidate()), range(4)))
    assert len(store.list("leads")) == 1
    assert len({v["id"] for v in values}) == 1


def test_reviews_and_sources_survive_a_new_store_connection():
    lead = qualified()
    other = StateStore(store.path)
    assert other.get("leads", lead["id"])["review"]["decision"] == "qualified"
    assert other.list("lead_reviews")[0]["lead_id"] == lead["id"]


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "http://127.0.0.1/x",
        "http://localhost/",
        "https://a:secret@example.test",
        "https://example.test:8000/",
    ],
)
def test_source_urls_are_public_links_without_credentials(url):
    with pytest.raises(ValueError):
        public_url(url)


def test_manual_csv_is_fully_validated_before_any_rows_write(api):
    csv = "name,location,source_url,email\nExample Bakery,Example Town,https://directory.example.test/bakery,owner@example.test\nBad,Example Town,javascript:bad,guess\n"
    assert api.post("/api/leads/import", json={"csv_text": csv}).status_code == 400
    assert store.list("leads") == []
    csv = "name,location,source_url,email\nExample Bakery,Example Town,https://directory.example.test/bakery,owner@example.test\n"
    first = api.post("/api/leads/import", json={"csv_text": csv})
    assert first.status_code == 200 and first.json()["unique_leads"] == 1
    api.post("/api/leads/import", json={"csv_text": csv})
    assert len(store.list("leads")) == 1
    assert store.list("contacts") == []
    assert (
        api.post(
            "/api/leads/import", json={"csv_text": csv.replace("email", "consent", 1)}
        ).status_code
        == 400
    )


def test_lead_routes_auth_limits_and_review_conflicts(api, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.get("/api/leads").status_code == 401
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    assert (
        api.post(
            "/api/leads/discover",
            json={
                "location": "Example Town",
                "latitude": 0,
                "longitude": 0,
                "radius_km": 100,
            },
        ).status_code
        == 422
    )
    lead = api.post(
        "/api/leads", json={k: v for k, v in candidate().items() if k != "source"}
    ).json()
    assert (
        api.put(
            f"/api/leads/{lead['id']}/review",
            json=review_payload(lead, decision="needs_review"),
        ).status_code
        == 200
    )
    assert (
        api.put(
            f"/api/leads/{lead['id']}/review", json=review_payload(lead)
        ).status_code
        == 409
    )
    assert (
        api.post(
            "/api/gmail/drafts",
            json={
                "purpose": "outreach",
                "recipient": "owner@example.test",
                "subject": "Hello",
                "body": "Hello",
            },
        ).status_code
        == 403
    )


def osm_data(website=False):
    return {
        "elements": [
            {
                "type": "node",
                "id": 123,
                "tags": {
                    "name": "Example Bakery",
                    "shop": "bakery",
                    "email": "owner@example.test",
                    **({"website": "bakery.example.test"} if website else {}),
                },
            }
        ]
    }


@pytest.mark.asyncio
async def test_osm_is_bounded_cached_and_does_not_infer_website_absence(monkeypatch):
    fetch = AsyncMock(return_value=osm_data())
    monkeypatch.setattr(lead_discovery, "request_overpass", fetch)
    args = {
        "location": "Example Town",
        "latitude": -26.5,
        "longitude": 29.5,
        "radius_km": 1,
        "limit": 5,
    }
    first = await lead_discovery.discover_osm(**args)
    second = await lead_discovery.discover_osm(**args)
    assert fetch.await_count == 1 and second["cached"]
    assert first["leads"][0]["source_url"] == "https://www.openstreetmap.org/node/123"
    assert first["leads"][0]["missing_website"] is None
    assert first["leads"][0]["status"] == "needs_review"
    assert "around:1000,-26.500000,29.500000" in fetch.await_args.args[0]
    assert "out center 6" in fetch.await_args.args[0]
    assert "© OpenStreetMap" in first["attribution"]
    with pytest.raises(ConflictError, match="cooldown"):
        await lead_discovery.discover_osm(**{**args, "longitude": 30})
    assert store.list("contacts") == []


@pytest.mark.asyncio
async def test_osm_failures_release_lease_no_fake_leads_and_daily_limit_is_shared(
    monkeypatch,
):
    fetch = AsyncMock(side_effect=lead_discovery.DiscoveryUnavailable("Unavailable"))
    monkeypatch.setattr(lead_discovery, "request_overpass", fetch)
    args = {"location": "Example Town", "latitude": -26.5, "longitude": 29.5}
    with pytest.raises(lead_discovery.DiscoveryUnavailable):
        await lead_discovery.discover_osm(**args)
    assert store.list("leads") == []
    assert store.get("leases", "public-lead-research") is None
    usage = store.get("research_limits", "overpass")
    store.put("research_limits", "overpass", {**usage, "last_request": 0, "count": 20})
    with pytest.raises(lead_discovery.DiscoveryUnavailable, match="Daily"):
        lead_discovery.reserve_request()
    assert fetch.await_count == 1


@pytest.mark.asyncio
async def test_osm_tagged_websites_are_recorded_as_unverified_evidence(monkeypatch):
    monkeypatch.setattr(
        lead_discovery,
        "request_overpass",
        AsyncMock(return_value=osm_data(website=True)),
    )
    data = await lead_discovery.discover_osm(
        location="Example Town", latitude=0, longitude=0
    )
    lead = data["leads"][0]
    assert lead["observation"]["website"] == "https://bakery.example.test"
    assert not lead_view(lead)["ready_to_draft"]


@pytest.mark.asyncio
async def test_core_uses_saved_candidates_and_paid_search_is_explicitly_disabled(
    monkeypatch,
):
    from tools import lead_finder

    network = Mock(side_effect=AssertionError("No paid request"))
    monkeypatch.setattr(lead_finder.httpx, "AsyncClient", network)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "fixture-key")
    with pytest.raises(RuntimeError, match="unavailable"):
        await lead_finder.search_businesses_without_websites("Example Town")
    lead = ingest_candidate(candidate())
    assert (await lead_finder.search_businesses_without_websites("Example Town"))[0][
        "id"
    ] == lead["id"]
    assert (await lead_finder.find_contact_email(lead["name"], lead["location"]))[
        "email"
    ] is None
    network.assert_not_called()


@pytest.mark.asyncio
async def test_unqualified_candidates_do_not_trigger_llm_or_portfolio_calls(
    monkeypatch,
):
    from agents import outreach_agent

    lead = ingest_candidate(candidate())
    llm = AsyncMock(side_effect=AssertionError("No LLM for unqualified candidates"))
    memory = AsyncMock(side_effect=AssertionError("No provider lookup"))
    monkeypatch.setattr(outreach_agent.llm_factory, "invoke_drafter", llm)
    monkeypatch.setattr(outreach_agent.memory_manager, "search_memory", memory)
    result = await outreach_agent.compose_pitch_node(
        {
            "enriched_leads": [
                {**lead, "confidence": "verified", "email": "owner@example.test"}
            ]
        }
    )
    assert result["drafted_pitches"] == []
    llm.assert_not_awaited()
    memory.assert_not_awaited()


@pytest.mark.asyncio
async def test_qualified_draft_is_reviewed_and_sent_once(monkeypatch):
    lead = qualified()
    draft = draft_lead(
        lead["id"], "Reviewed subject", "Reviewed message", email_service.expected_email
    )
    same = draft_lead(
        lead["id"],
        "Replacement subject",
        "Replacement message",
        email_service.expected_email,
    )
    assert same["id"] == draft["id"] and same["draft_response"] == "Reviewed message"
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    await approve_draft(draft["id"])
    await approve_draft(draft["id"])
    assert messages.send.call_count == 1
    assert store.get("approvals", draft["id"])["status"] == "sent"


@pytest.mark.asyncio
async def test_changed_source_or_recipient_blocks_already_queued_outreach(monkeypatch):
    lead = qualified()
    draft = draft_lead(lead["id"], "Subject", "Hello", email_service.expected_email)
    ingest_candidate(candidate(website="https://bakery.example.test"))
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EligibilityError):
        await approve_draft(draft["id"])
    assert messages.send.call_count == 0
    assert store.get("approvals", draft["id"])["status"] == "pending"
    changed = store.get("leads", lead["id"])
    review_lead(lead["id"], review_payload(changed, email="new-owner@example.test"))
    with pytest.raises(EligibilityError, match="recipient"):
        await approve_draft(draft["id"])
    assert messages.send.call_count == 0


@pytest.mark.asyncio
async def test_last_moment_review_change_is_rechecked_before_provider_send(monkeypatch):
    lead = qualified()
    draft = draft_lead(lead["id"], "Subject", "Hello", email_service.expected_email)
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    original = email_service.get_profile

    async def changed_during_preflight():
        profile = await original()
        ingest_candidate(candidate(website="https://bakery.example.test"))
        return profile

    monkeypatch.setattr(email_service, "get_profile", changed_during_preflight)
    with pytest.raises(EligibilityError):
        await approve_draft(draft["id"])
    assert messages.send.call_count == 0
    assert store.get("approvals", draft["id"])["status"] == "failed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [b'{"remark":"runtime timeout","elements":[]}', b"not json", b"x" * 3000001],
)
async def test_public_search_rejects_incomplete_invalid_or_oversized_responses(
    monkeypatch, content
):
    class Response:
        def raise_for_status(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def aiter_bytes(self):
            yield content

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, method, endpoint, **kwargs):
            assert method == "POST"
            assert endpoint == lead_discovery.ENDPOINT
            return Response()

    monkeypatch.setattr(lead_discovery.httpx, "AsyncClient", lambda **kwargs: Client())
    with pytest.raises(lead_discovery.DiscoveryUnavailable):
        await lead_discovery.request_overpass("[out:json];node(0);out;")
    assert store.list("leads") == []


def test_rejected_records_do_not_gain_qualification_on_rediscovery():
    lead = ingest_candidate(candidate())
    reviewed = review_lead(
        lead["id"],
        review_payload(lead, decision="rejected", decision_note="Unsuitable"),
    )
    again = ingest_candidate(candidate(website="https://bakery.example.test"))
    assert again["status"] == "rejected"
    assert again["review"] == reviewed["review"]
    with pytest.raises(EligibilityError):
        ensure_qualified(lead["id"])


def test_previous_legacy_outreach_cannot_be_duplicated_by_new_lead_flow():
    lead = qualified()
    store.put(
        "messages",
        "legacy",
        {
            "from": email_service.expected_email,
            "to": "owner@example.test",
            "purpose": "outreach",
            "status": "sent",
        },
    )
    with pytest.raises(EligibilityError, match="already exists"):
        draft_lead(lead["id"], "Hello", "Hello", email_service.expected_email)
