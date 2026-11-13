"""Fresh retrievals and new reviews must not renew old activity evidence."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock

import pytest
from core.store import store
from agents.human_approval import approve_draft
from services import lead_discovery
from services.contacts import EligibilityError
from services.email_service import email_service
from services.lead_service import (
    ingest_candidate,
    review_lead,
    ensure_qualified,
    lead_view,
    draft_lead,
)
from test_leads_phase4 import candidate, qualified, review_payload
from test_foundation import gmail_client


@pytest.fixture
def api():
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        yield client


def day(offset=0):
    return (
        datetime.now(ZoneInfo("Africa/Johannesburg")).date() + timedelta(days=offset)
    ).isoformat()


@pytest.mark.parametrize(
    "changes",
    [
        {"activity_date": ""},
        {"activity_date": "2018-01-01"},
        {"activity_date": day(1)},
        {"activity_date": "2026-99-01"},
        {"activity_method": ""},
        {"identity_source": "https://www.openstreetmap.org/node/123"},
    ],
)
def test_missing_old_future_or_map_only_activity_cannot_qualify(changes):
    lead = ingest_candidate(candidate())
    with pytest.raises(ValueError):
        review_lead(lead["id"], review_payload(lead, **changes))


@pytest.mark.parametrize("method", ["direct_confirmation", "local_observation"])
def test_current_call_or_visit_can_support_activity_with_branch_identity_link(method):
    lead = ingest_candidate(
        candidate(source_url="https://www.openstreetmap.org/node/123")
    )
    reviewed = review_lead(
        lead["id"],
        review_payload(
            lead,
            activity_method=method,
            activity_date=day(),
            identity_note="Operator confirmed this exact branch is trading during a visit/call today",
        ),
    )
    assert ensure_qualified(reviewed["id"], require_consent=False)


def test_closed_business_can_be_rejected_without_other_evidence_and_stays_rejected(api):
    lead = ingest_candidate(candidate())
    result = api.put(
        f"/api/leads/{lead['id']}/review",
        json={
            "revision": lead["revision"],
            "business_status": "inactive",
            "decision": "rejected",
            "decision_note": "I know this branch has closed",
        },
    )
    assert result.status_code == 200
    again = ingest_candidate(candidate(source_updated_at="2026-10-17T00:00:00Z"))
    assert again["status"] == "rejected"
    assert not lead_view(again)["ready_to_draft"]


@pytest.mark.asyncio
async def test_expired_activity_blocks_queued_send_even_with_fresh_review(monkeypatch):
    lead = qualified()
    draft = draft_lead(lead["id"], "Website", "Hello", email_service.expected_email)
    lead["review"]["activity_date"] = day(-31)
    store.put("leads", lead["id"], lead)
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EligibilityError):
        await approve_draft(draft["id"])
    assert messages.send.call_count == 0
    # Re-saving today does not renew the old activity evidence date.
    with pytest.raises(ValueError):
        review_lead(lead["id"], review_payload(lead, activity_date=day(-31)))


def test_legacy_qualification_requires_activity_evidence_again():
    lead = qualified()
    lead["review"].pop("activity_date")
    lead["review"].pop("activity_method")
    store.put("leads", lead["id"], lead)
    assert not lead_view(lead)["ready_to_draft"]


@pytest.mark.asyncio
async def test_old_map_metadata_is_preserved_without_claiming_current_activity(
    monkeypatch,
):
    fetch = AsyncMock(
        return_value={
            "elements": [
                {
                    "type": "node",
                    "id": 123,
                    "timestamp": "2018-01-01T00:00:00Z",
                    "user": "should-not-be-stored",
                    "uid": 987,
                    "tags": {
                        "name": "Closed Shop",
                        "shop": "furniture",
                        "check_date": "2017-12-01",
                    },
                }
            ]
        }
    )
    monkeypatch.setattr(lead_discovery, "request_overpass", fetch)
    result = await lead_discovery.discover_osm(
        location="Example Town", latitude=0, longitude=0
    )
    lead = result["leads"][0]
    assert lead["observation"]["source_updated_at"] == "2018-01-01T00:00:00Z"
    assert lead["observation"]["source_check_date"] == "2017-12-01"
    assert "user" not in lead["observation"] and "uid" not in lead["observation"]
    assert lead_view(lead)["source_freshness"]["status"] == "old"
    assert lead["status"] == "needs_review" and lead["review"] is None
    assert "out meta center" in fetch.await_args.args[0]


@pytest.mark.parametrize("stamp", ["", "invalid", "2018-01-01T00:00:00"])
def test_unknown_or_invalid_map_date_stays_unknown(stamp):
    lead = ingest_candidate(candidate(source_updated_at=stamp))
    assert lead_view(lead)["source_freshness"] == {
        "status": "unknown",
        "age_days": None,
    }
