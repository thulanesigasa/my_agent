"""Scheduled campaigns prepare bounded approvals, never messages or permissions."""

import asyncio
import threading
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import settings
from core.store import store, StateStore, ConflictError
from services import campaigns
from services.contacts import save_contact, suppress, EligibilityError
from services.email_service import email_service
from services.lead_service import ingest_candidate, review_lead, draft_lead
from services.report_service import TZ
from services.send_controls import Controls, update as update_sending_controls
from test_leads_phase4 import candidate, review_payload


def leads(count=3, offset=0):
    result = []
    for i in range(offset, offset + count):
        email = f"owner{i}@example.test"
        lead = ingest_candidate(
            candidate(
                name=f"Bakery {i}",
                address=f"{i} Main Street",
                email=email,
                source_url=f"https://business.example.test/{i}",
            )
        )
        save_contact(
            email,
            verified=True,
            consent="granted",
            evidence="Explicit fixture permission",
        )
        result.append(review_lead(lead["id"], review_payload(lead, email=email)))
    return result


def create(members=None, **changes):
    members = members or leads()
    payload = campaigns.CampaignInput(
        name="Local bakeries",
        lead_ids=[lead["id"] for lead in members],
        weekdays_only=False,
        **changes,
    )
    return campaigns.create(payload, email_service.expected_email)


def activate(campaign):
    return campaigns.control(
        campaign["id"], email_service.expected_email, "resume", campaign["version"]
    )


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def test_campaign_starts_paused_and_creation_has_no_side_effects():
    c = create()
    assert c["status"] == "paused" and c["next_run_at"] is None and c["cursor"] == 0
    assert (
        store.list("approvals")
        == store.list("messages")
        == store.list("campaign_runs")
        == []
    )
    with pytest.raises(ConflictError, match="Resume"):
        campaigns.run_campaign(c["id"], email_service.expected_email)


@pytest.mark.parametrize(
    "changes",
    [
        {"lead_ids": []},
        {"lead_ids": ["x", "x"]},
        {"local_time": "25:00"},
        {"local_time": "9:00"},
        {"batch_size": 0},
        {"batch_size": 6},
        {"name": "\nInjected"},
        {"automatic_sending": True},
    ],
)
def test_invalid_campaign_configuration_is_rejected(changes):
    with pytest.raises(ValidationError):
        campaigns.CampaignInput(**{"name": "Pilot", "lead_ids": ["saved"], **changes})


def test_creation_requires_existing_qualified_leads_and_mailbox():
    lead = ingest_candidate(candidate())
    payload = campaigns.CampaignInput(name="Pilot", lead_ids=[lead["id"]])
    with pytest.raises(EligibilityError):
        campaigns.create(payload, email_service.expected_email)
    with pytest.raises(EligibilityError, match="Connect Gmail"):
        campaigns.create(payload, "")
    assert store.list("campaigns") == []


def test_schedule_is_sast_and_weekend_runs_move_to_monday():
    c = {"local_time": "09:00", "weekdays_only": True}
    friday = datetime(2026, 10, 16, 10, tzinfo=TZ)
    assert campaigns.next_time(c, friday) == "2026-10-19T09:00:00+02:00"
    monday = datetime(2026, 10, 19, 8, tzinfo=TZ)
    assert campaigns.next_time(c, monday) == "2026-10-19T09:00:00+02:00"


def test_scheduled_overdue_weekend_batch_waits_until_monday():
    c = activate(create())
    store.put(
        "campaigns",
        c["id"],
        {**c, "weekdays_only": True, "next_run_at": "2026-10-16T09:00:00+02:00"},
    )
    run = campaigns.run_campaign(
        c["id"],
        email_service.expected_email,
        manual=False,
        at=datetime(2026, 10, 18, 10, tzinfo=TZ),
    )
    assert run is None and store.list("approvals") == []
    assert store.get("campaigns", c["id"])["next_run_at"] == "2026-10-19T09:00:00+02:00"


def test_only_five_unfinished_campaigns_are_allowed_and_cancellation_frees_a_slot():
    members = leads(1)
    existing = [create(members) for _ in range(5)]
    with pytest.raises(ValueError, match="five unfinished"):
        create(members)
    campaigns.control(
        existing[0]["id"],
        email_service.expected_email,
        "cancel",
        existing[0]["version"],
    )
    assert create(members)["status"] == "paused"


def test_shutdown_flag_pauses_claimed_batch_before_drafting():
    c = activate(create())
    run = campaigns.run_campaign(
        c["id"], email_service.expected_email, stop=lambda: True
    )
    assert run["status"] == "interrupted"
    assert store.get("campaigns", c["id"])["status"] == "paused"
    assert campaigns.usage()["used"] == 0 and store.list("approvals") == []


def test_one_batch_per_day_advances_fixed_members_and_never_sends(monkeypatch):
    from services.llm_factory import llm_factory
    from core.memory import memory_manager

    model = AsyncMock(side_effect=AssertionError("No model calls"))
    memory = AsyncMock(side_effect=AssertionError("No memory-provider calls"))
    sending = AsyncMock(side_effect=AssertionError("Campaigns cannot send"))
    monkeypatch.setattr(llm_factory, "invoke_drafter", model)
    monkeypatch.setattr(memory_manager, "search_memory", memory)
    monkeypatch.setattr(email_service, "send_email", sending)
    c = activate(create(batch_size=2))
    first = campaigns.run_campaign(c["id"], email_service.expected_email)
    assert len(first["results"]) == 2 and all(
        r["decision"] == "queued" for r in first["results"]
    )
    assert StateStore(store.path).get("campaigns", c["id"])["cursor"] == 2
    with pytest.raises(ConflictError, match="already ran today"):
        campaigns.run_campaign(c["id"], email_service.expected_email)
    second = campaigns.run_campaign(
        c["id"], email_service.expected_email, at=datetime.now(TZ) + timedelta(days=1)
    )
    assert len(second["results"]) == 1
    assert store.get("campaigns", c["id"])["status"] == "completed"
    assert len(store.list("approvals")) == 3 and store.list("messages") == []
    assert all(
        a["status"] == "pending" and a["campaign_source"]["name"] == c["name"]
        for a in store.list("approvals")
    )
    model.assert_not_awaited()
    memory.assert_not_awaited()
    sending.assert_not_awaited()


def test_repeat_campaign_preserves_existing_approval_and_source():
    members = leads(1)
    first = activate(create(members))
    campaigns.run_campaign(first["id"], email_service.expected_email)
    approval = store.list("approvals")[0]
    second = activate(create(members))
    result = campaigns.run_campaign(second["id"], email_service.expected_email)
    assert result["results"][0]["decision"] == "existing_approval"
    assert store.list("approvals") == [approval]


def test_qualification_is_rechecked_and_skipped_leads_consume_a_draft_slot():
    members = leads(1)
    c = activate(create(members))
    suppress(members[0]["review"]["email"], "Stop")
    run = campaigns.run_campaign(c["id"], email_service.expected_email)
    assert run["results"][0]["decision"] == "skipped"
    assert store.get("campaigns", c["id"])["cursor"] == 1
    assert campaigns.usage()["used"] == 1 and store.list("approvals") == []
    assert (
        store.get("contacts", members[0]["review"]["email"])["consent"]
        == "unsubscribed"
    )


def test_global_daily_draft_budget_is_shared_across_campaigns():
    jobs = [activate(create(leads(5, offset=i * 5), batch_size=5)) for i in range(3)]
    for c in jobs[:2]:
        campaigns.run_campaign(c["id"], email_service.expected_email)
    run = campaigns.run_campaign(jobs[2]["id"], email_service.expected_email)
    assert run["status"] == "daily_budget_reached" and run["results"] == []
    assert store.get("campaigns", jobs[2]["id"])["cursor"] == 0
    assert campaigns.usage()["used"] == 10 and len(store.list("approvals")) == 10
    next_day = datetime.now(TZ) + timedelta(days=1)
    run = campaigns.run_campaign(
        jobs[2]["id"], email_service.expected_email, at=next_day
    )
    assert len(run["results"]) == 5 and campaigns.usage(next_day)["used"] == 5


def test_pause_during_a_step_keeps_saved_draft_and_stops_next_lead(monkeypatch):
    c = activate(create())
    compose = campaigns.create_preview

    def pause_after_start(*args):
        current = store.get("campaigns", c["id"])
        campaigns.control(
            c["id"], email_service.expected_email, "pause", current["version"]
        )
        return compose(*args)

    monkeypatch.setattr(campaigns, "create_preview", pause_after_start)
    run = campaigns.run_campaign(c["id"], email_service.expected_email)
    assert run["status"] == "paused" and len(run["results"]) == 1
    current = store.get("campaigns", c["id"])
    assert current["status"] == "paused" and current["cursor"] == 1
    resumed = activate(current)
    assert (
        datetime.fromisoformat(resumed["next_run_at"]).date() > datetime.now(TZ).date()
    )


def test_cancel_is_terminal_and_stale_control_does_not_overwrite_it():
    c = activate(create())
    campaigns.control(c["id"], email_service.expected_email, "cancel", c["version"])
    with pytest.raises(ConflictError):
        campaigns.control(c["id"], email_service.expected_email, "resume", c["version"])
    assert store.get("campaigns", c["id"])["status"] == "cancelled"


def test_live_worker_lease_blocks_a_second_runner():
    c = activate(create())
    store.acquire_lease(campaigns.LEASE, "other-worker", seconds=120)
    with pytest.raises(ConflictError, match="Another campaign"):
        campaigns.run_campaign(c["id"], email_service.expected_email)
    assert not campaigns.run_due() and store.list("approvals") == []


def test_interrupted_run_pauses_on_recovery_and_does_not_replay_existing_draft():
    members = leads(2)
    c = activate(create(members))
    # Simulate a crash after approval publication but before cursor advancement.
    interrupted = campaigns._claim(
        c["id"], email_service.expected_email, datetime.now(TZ), True
    )
    existing = draft_lead(
        members[0]["id"],
        "Reviewed subject",
        "Reviewed body",
        email_service.expected_email,
    )
    assert not campaigns.run_due()
    current = store.get("campaigns", c["id"])
    assert current["status"] == "paused" and current["cursor"] == 0
    assert store.get("campaign_runs", interrupted["id"])["status"] == "interrupted"
    activate(current)
    run = campaigns.run_campaign(
        c["id"], email_service.expected_email, at=datetime.now(TZ) + timedelta(days=1)
    )
    assert run["results"][0]["decision"] == "existing_approval"
    assert store.get("approvals", existing["id"])["draft_response"] == "Reviewed body"
    assert len(store.list("approvals")) == 2


def test_unexpected_failure_pauses_campaign_without_advancing_cursor(monkeypatch):
    c = activate(create())

    def fail(*args):
        raise RuntimeError("Simulated local failure")

    monkeypatch.setattr(campaigns, "create_preview", fail)
    with pytest.raises(RuntimeError):
        campaigns.run_campaign(c["id"], email_service.expected_email)
    current = store.get("campaigns", c["id"])
    assert current["status"] == "paused" and current["cursor"] == 0
    assert store.list("campaign_runs")[0]["status"] == "failed"
    assert campaigns.usage()["used"] == 1


def test_worker_only_runs_due_campaigns_and_filters_current_mailbox():
    c = activate(create())
    assert not campaigns.run_due()
    store.put(
        "campaigns",
        c["id"],
        {**c, "next_run_at": (datetime.now(TZ) - timedelta(seconds=1)).isoformat()},
    )
    assert campaigns.run_due()
    assert len(store.list("approvals")) == 3


def test_business_send_pause_does_not_disable_campaign_drafting():
    update_sending_controls(Controls(version=0, paused=True, daily_limit=1))
    c = activate(create())
    campaigns.run_campaign(c["id"], email_service.expected_email)
    assert len(store.list("approvals")) == 3 and store.list("messages") == []


@pytest.mark.asyncio
async def test_runner_start_stop_waits_for_local_tick(monkeypatch):
    started = threading.Event()

    def tick(stop):
        started.set()
        return False

    monkeypatch.setattr(campaigns, "run_due", tick)
    runner = campaigns.CampaignRunner()
    runner.start()
    assert await asyncio.to_thread(started.wait, 2)
    await runner.stop()
    assert runner.task is None


def test_api_auth_mailbox_scope_and_control_versions(api, monkeypatch):
    members = leads(1)
    payload = {"name": "Pilot", "lead_ids": [members[0]["id"]]}
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.get("/api/campaigns").status_code == 401
    assert api.post("/api/campaigns", json=payload).status_code == 401
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    c = api.post("/api/campaigns", json=payload).json()
    path = f"/api/campaigns/{c['id']}"
    assert api.post(path + "/run").status_code == 409
    assert (
        api.patch(path, json={"action": "resume", "version": c["version"]}).status_code
        == 200
    )
    assert (
        api.patch(path, json={"action": "pause", "version": c["version"]}).status_code
        == 409
    )
    assert api.post(path + "/run").status_code == 200
    assert api.get("/api/campaigns").json()["automatic_sending"] is False
    monkeypatch.setattr(email_service, "expected_email", "other@example.test")
    assert api.get("/api/campaigns").json()["campaigns"] == []
    assert api.post(path + "/run").status_code == 404
