"""Business dispatch policy reservations are local, durable and atomic."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import settings
from core.store import store, StateStore, ConflictError
from services import send_controls as controls
from services.contacts import EligibilityError
from services.email_service import email_service, DeliveryUnknown, EmailUnavailable
from services.lead_service import draft_lead
from agents.human_approval import approve_draft
from test_leads_phase4 import qualified
from test_foundation import gmail_client


def change(**changes):
    config = controls.status(email_service.expected_email)["config"]
    return controls.update(controls.Controls(**{**config, **changes}))


def draft():
    lead = qualified()
    return draft_lead(
        lead["id"], "Website", "Reviewed body", email_service.expected_email
    )


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def test_default_policy_is_five_attempts_and_does_not_queue_or_send():
    status = controls.status(email_service.expected_email)
    assert status["config"] == {"version": 0, "paused": False, "daily_limit": 5}
    assert status["remaining"] == 5 and status["used"] == 0
    assert status["timezone"] == "Africa/Johannesburg"
    assert store.list("messages") == store.list("approvals") == []


def test_controls_persist_and_stale_editor_cannot_overwrite_pause():
    before = controls.Controls(
        **controls.status(email_service.expected_email)["config"]
    )
    change(paused=True, daily_limit=2)
    assert StateStore(store.path).get("send_controls", "current")["config"]["paused"]
    with pytest.raises(ConflictError):
        controls.update(before)
    assert controls.status(email_service.expected_email)["config"]["paused"]


@pytest.mark.parametrize("limit", [0, -1, 26, 100])
def test_limits_are_bounded(limit):
    with pytest.raises(ValidationError):
        controls.Controls(version=0, paused=False, daily_limit=limit)


def test_parallel_reservations_cannot_overspend_daily_allowance():
    change(daily_limit=2)

    def reserve(index):
        try:
            return controls.reserve(
                email_service.expected_email, "outreach", f"dispatch-{index}"
            )
        except EligibilityError:
            return None

    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(workers.map(reserve, range(8)))
    assert sum(r is not None for r in results) == 2
    assert controls.status(email_service.expected_email)["used"] == 2
    assert controls.status(email_service.expected_email)["remaining"] == 0


def test_outreach_and_replies_share_allowance_but_each_mailbox_has_its_own():
    change(daily_limit=2)
    controls.reserve(email_service.expected_email, "outreach", "first")
    controls.reserve(email_service.expected_email, "reply", "second")
    with pytest.raises(EligibilityError):
        controls.reserve(email_service.expected_email, "outreach", "followup")
    assert controls.reserve("other@example.test", "outreach", "other")


def test_duplicate_dispatch_reservation_cannot_be_replayed():
    controls.reserve(email_service.expected_email, "outreach", "same-id")
    with pytest.raises(EligibilityError, match="already reserved"):
        controls.reserve(email_service.expected_email, "outreach", "same-id")
    assert controls.status(email_service.expected_email)["used"] == 1


def test_daily_reset_occurs_at_midnight_sast():
    change(daily_limit=1)
    before = datetime(2026, 10, 17, 21, 59, 59, tzinfo=timezone.utc)
    after = datetime(2026, 10, 17, 22, 0, 0, tzinfo=timezone.utc)
    controls.reserve(email_service.expected_email, "outreach", "day-1", at=before)
    assert controls.status(email_service.expected_email, at=before)["remaining"] == 0
    assert controls.status(email_service.expected_email, at=after)["remaining"] == 1
    controls.reserve(email_service.expected_email, "reply", "day-2", at=after)
    status = controls.status(email_service.expected_email, at=after)
    assert status["day"] == "2026-10-18" and status["used"] == 1
    assert status["resets_at"] == "2026-10-19T00:00:00+02:00"


def test_limit_edits_do_not_erase_usage_and_midnight_does_not_clear_pause():
    controls.reserve(email_service.expected_email, "outreach", "first")
    controls.reserve(email_service.expected_email, "reply", "second")
    change(daily_limit=1)
    assert controls.status(email_service.expected_email)["remaining"] == 0
    change(daily_limit=3, paused=True)
    assert controls.status(email_service.expected_email)["remaining"] == 1
    assert controls.status(
        email_service.expected_email, at=datetime(2027, 1, 1, tzinfo=timezone.utc)
    )["config"]["paused"]


@pytest.mark.asyncio
async def test_known_provider_failure_and_explicit_retry_use_separate_slots(
    monkeypatch,
):
    from test_gmail_phase2 import http_error

    item = draft()
    client, failed_messages = gmail_client(error=http_error(429))
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EmailUnavailable):
        await approve_draft(item["id"])
    assert controls.status(email_service.expected_email)["used"] == 1
    client, sent_messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    await approve_draft(item["id"])
    assert controls.status(email_service.expected_email)["used"] == 2
    assert failed_messages.send.call_count == sent_messages.send.call_count == 1


def test_upgrade_includes_legacy_confirmed_and_uncertain_submissions_without_double_counting():
    for index, status in enumerate(("sent", "sending", "delivery_unknown", "failed")):
        store.put(
            "messages",
            f"old-{index}",
            {
                "from": email_service.expected_email,
                "purpose": "outreach",
                "status": status,
            },
        )
    usage = controls.status(email_service.expected_email)
    assert usage["legacy_submissions"] == 3 and usage["used"] == 3
    store.put(
        "messages",
        "modern",
        {
            "from": email_service.expected_email,
            "purpose": "reply",
            "status": "sent",
            "send_controls_version": 1,
        },
    )
    controls.reserve(email_service.expected_email, "reply", "modern")
    assert controls.status(email_service.expected_email)["used"] == 4


def test_pause_does_not_apply_to_test_report_or_internal_notification_reservations():
    change(paused=True)
    for purpose in ("test", "report", "notification"):
        assert controls.reserve(email_service.expected_email, purpose, purpose) is None
        controls.check_available(email_service.expected_email, purpose)
    with pytest.raises(EligibilityError, match="paused"):
        controls.reserve(email_service.expected_email, "reply", "business")
    assert controls.status(email_service.expected_email)["used"] == 0


@pytest.mark.asyncio
async def test_pause_blocks_approval_without_losing_its_reviewed_content(monkeypatch):
    item = draft()
    change(paused=True)
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EligibilityError, match="paused"):
        await approve_draft(item["id"])
    assert store.get("approvals", item["id"])["status"] == "pending"
    assert messages.send.call_count == 0 and store.list("send_attempts") == []
    change(paused=False)
    await approve_draft(item["id"])
    await approve_draft(item["id"])
    assert messages.send.call_count == 1
    assert controls.status(email_service.expected_email)["used"] == 1


@pytest.mark.asyncio
async def test_pause_activated_during_preflight_blocks_provider_submission(monkeypatch):
    item = draft()
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    original_profile = email_service.get_profile

    async def paused():
        profile = await original_profile()
        change(paused=True)
        return profile

    monkeypatch.setattr(email_service, "get_profile", paused)
    with pytest.raises(EligibilityError, match="paused"):
        await approve_draft(item["id"])
    assert messages.send.call_count == 0
    assert store.get("approvals", item["id"])["status"] == "failed"
    assert controls.status(email_service.expected_email)["used"] == 0


@pytest.mark.asyncio
async def test_daily_limit_blocks_new_attempt_and_keeps_existing_draft(monkeypatch):
    item = draft()
    change(daily_limit=1)
    controls.reserve(email_service.expected_email, "reply", "earlier-attempt")
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EligibilityError, match="limit reached"):
        await approve_draft(item["id"])
    assert (
        messages.send.call_count == 0
        and store.get("approvals", item["id"])["status"] == "pending"
    )


@pytest.mark.asyncio
async def test_uncertain_submission_keeps_reserved_slot_and_cannot_be_reapproved(
    monkeypatch,
):
    item = draft()
    client, messages = gmail_client(error=TimeoutError("Provider timeout"))
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(DeliveryUnknown):
        await approve_draft(item["id"])
    assert controls.status(email_service.expected_email)["used"] == 1
    with pytest.raises(ConflictError):
        await approve_draft(item["id"])
    assert messages.send.call_count == 1


@pytest.mark.asyncio
async def test_direct_business_adapter_calls_are_metered(monkeypatch):
    change(daily_limit=1)
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    await email_service.send_email(
        "owner@example.test", "Subject", "Body", purpose="outreach"
    )
    with pytest.raises(EligibilityError):
        await email_service.send_email(
            "owner@example.test", "Subject", "Body", purpose="reply"
        )
    assert (
        messages.send.call_count == 1
        and controls.status(email_service.expected_email)["used"] == 1
    )


def test_api_auth_validation_cas_and_read_only_usage(api, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.get("/api/sending-controls").status_code == 401
    assert (
        api.put(
            "/api/sending-controls",
            json={"version": 0, "paused": True, "daily_limit": 5},
        ).status_code
        == 401
    )
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    value = api.get("/api/sending-controls").json()
    config = {**value["config"], "paused": True}
    assert api.put("/api/sending-controls", json=config).status_code == 200
    assert api.put("/api/sending-controls", json=config).status_code == 409
    assert (
        api.put(
            "/api/sending-controls", json={**config, "daily_limit": 100}
        ).status_code
        == 422
    )
    assert store.list("messages") == store.list("approvals") == []
    assert any(
        event["kind"] == "sending.controls_changed" for event in store.activities()
    )
