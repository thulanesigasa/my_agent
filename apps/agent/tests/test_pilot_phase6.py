"""Local pilot evidence and campaign previews must not mutate the workflow."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from config import settings
from core.store import store
from services import pilot, campaigns
from services.contacts import suppress
from services.email_service import email_service
from services.lead_service import draft_lead
from services.send_controls import Controls, update
from test_campaigns_phase6 import create, leads, activate


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def ledger():
    with store.connect() as db:
        return (
            db.execute("SELECT * FROM records ORDER BY kind,id").fetchall(),
            db.execute("SELECT * FROM activity ORDER BY id").fetchall(),
        )


def check(report, name):
    return next(item for item in report["checks"] if item["name"] == name)


def test_dry_run_on_paused_campaign_previews_without_any_mutation():
    c = create()
    before = ledger()
    result = pilot.dry_run(c["id"], email_service.expected_email)
    assert result["read_only"] and result["campaign_status"] == "paused"
    assert "paused" in result["run_blockers"][0]
    assert all(
        row["decision"] == "would_queue" and row["recipient"] and row["body"]
        for row in result["rows"]
    )
    assert ledger() == before
    assert store.list("proposal_previews") == store.list("approvals") == []


def test_dry_run_and_real_batch_use_the_same_message_composition():
    c = create(leads(1))
    result = pilot.dry_run(c["id"], email_service.expected_email)
    activate(c)
    campaigns.run_campaign(c["id"], email_service.expected_email)
    approval = store.list("approvals")[0]
    assert result["rows"][0]["subject"] == approval["subject"]
    assert result["rows"][0]["body"] == approval["draft_response"]


def test_existing_approval_displays_its_actual_saved_content():
    members = leads(1)
    c = create(members)
    original = draft_lead(
        members[0]["id"],
        "Operator subject",
        "Exact edited content",
        email_service.expected_email,
    )
    before = ledger()
    row = pilot.dry_run(c["id"], email_service.expected_email)["rows"][0]
    assert row["decision"] == "existing_approval"
    assert (
        row["subject"] == original["subject"] and row["body"] == "Exact edited content"
    )
    assert ledger() == before


def test_legacy_submission_and_suppression_show_actual_queue_blockers():
    members = leads(2)
    c = create(members)
    store.put(
        "messages",
        "legacy",
        {
            "from": email_service.expected_email,
            "to": members[0]["review"]["email"],
            "purpose": "outreach",
            "status": "sent",
        },
    )
    suppress(members[1]["review"]["email"], "Stop")
    before = ledger()
    rows = pilot.dry_run(c["id"], email_service.expected_email)["rows"]
    assert all(row["decision"] == "blocked" and not row["body"] for row in rows)
    assert "already exists" in rows[0]["reason"]
    assert ledger() == before


def test_preview_does_not_reserve_quota_or_change_a_claimed_run():
    c = activate(create())
    campaigns._claim(
        c["id"], email_service.expected_email, datetime.now(campaigns.TZ), True
    )
    before = ledger()
    report = pilot.dry_run(c["id"], email_service.expected_email)
    assert any("already claimed" in reason for reason in report["run_blockers"])
    assert ledger() == before and store.list("campaign_runs")[0]["status"] == "running"


def test_dry_run_reflects_exhausted_campaign_budget_and_separate_sending_pause():
    c = create(leads(1))
    for index in range(10):
        store.put("campaign_draft_slots", str(index), {"day": campaigns.usage()["day"]})
    update(Controls(version=0, paused=True, daily_limit=1))
    before = ledger()
    report = pilot.dry_run(c["id"], email_service.expected_email)
    assert report["rows"][0]["decision"] == "budget_blocked"
    assert report["sending"]["config"]["paused"]
    assert report["draft_budget"]["remaining"] == 0 and ledger() == before


def test_readiness_missing_setup_does_not_invent_a_pass_or_overall_ready_status():
    report = pilot.readiness(email_service.expected_email)
    assert report["read_only"] and "ready" not in report
    assert check(report, "Recorded account verification")["status"] == "action"
    assert check(report, "Owned-mailbox send and reply evidence")["status"] == "action"
    assert check(report, "Eligible business leads")["status"] == "action"
    assert "Local evidence only" in report["warning"]


def test_recorded_account_verification_must_match_current_mailbox(monkeypatch):
    monkeypatch.setattr(email_service, "is_configured", True)
    store.put(
        "gmail_connection",
        "current",
        {"status": "verified", "email": "other@example.test"},
    )
    assert (
        check(
            pilot.readiness(email_service.expected_email),
            "Recorded account verification",
        )["status"]
        == "action"
    )
    store.put(
        "gmail_connection",
        "current",
        {"status": "verified", "email": email_service.expected_email},
    )
    assert (
        check(
            pilot.readiness(email_service.expected_email),
            "Recorded account verification",
        )["status"]
        == "pass"
    )


def test_recorded_owned_mailbox_cycle_requires_provider_confirmation_and_a_matched_human_reply():
    sent = store.put(
        "messages",
        "test-send",
        {
            "from": email_service.expected_email,
            "to": "owned@example.test",
            "purpose": "test",
            "status": "sent",
            "provider_message_id": "provider-test",
            "thread_id": "thread-test",
        },
    )
    received_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    store.put(
        "inbox",
        "test-reply",
        {
            "mailbox": email_service.expected_email,
            "sender": "owned@example.test",
            "thread_id": "thread-test",
            "matched_outbound_id": sent["id"],
            "provider_timestamp": str(int(received_at.timestamp() * 1000)),
            "automated": False,
        },
    )
    before = ledger()
    report = pilot.readiness(
        email_service.expected_email, at=received_at + timedelta(seconds=1)
    )
    assert check(report, "Owned-mailbox send and reply evidence")["status"] == "pass"
    assert ledger() == before


@pytest.mark.parametrize(
    "change",
    [
        {"automated": True},
        {"bounce": True},
        {"sender": "stranger@example.test"},
        {"matched_outbound_id": "other"},
        {"thread_id": "different"},
        {"provider_timestamp": "future"},
    ],
)
def test_invalid_or_automated_reply_does_not_prove_test_cycle(change):
    store.put(
        "messages",
        "test",
        {
            "from": email_service.expected_email,
            "to": "owned@example.test",
            "purpose": "test",
            "status": "sent",
            "provider_message_id": "provider-test",
            "thread_id": "thread-test",
        },
    )
    at = datetime.now(timezone.utc) + timedelta(seconds=2)
    change = {**change}
    if change.get("provider_timestamp") == "future":
        change["provider_timestamp"] = str(
            int((at + timedelta(days=1)).timestamp() * 1000)
        )
    store.put(
        "inbox",
        "incoming",
        {
            "mailbox": email_service.expected_email,
            "sender": "owned@example.test",
            "thread_id": "thread-test",
            "matched_outbound_id": "test",
            "provider_timestamp": str(
                int((at - timedelta(seconds=1)).timestamp() * 1000)
            ),
            **change,
        },
    )
    assert (
        check(
            pilot.readiness(email_service.expected_email, at=at),
            "Owned-mailbox send and reply evidence",
        )["status"]
        == "action"
    )


def test_readiness_deduplicates_correlated_uncertain_submission_and_approval():
    store.put(
        "messages",
        "dispatch",
        {"from": email_service.expected_email, "status": "delivery_unknown"},
    )
    store.put(
        "approvals",
        "held",
        {
            "sender_mailbox": email_service.expected_email,
            "status": "delivery_unknown",
            "dispatch_id": "dispatch",
        },
    )
    report = pilot.readiness(email_service.expected_email)
    evidence = check(report, "Submission reconciliation")
    assert evidence["status"] == "action" and evidence["detail"].startswith(
        "1 submission"
    )


def test_stale_or_future_sync_metadata_never_counts_as_recent():
    at = datetime.now(timezone.utc)
    for seconds in (-901, 60):
        with store.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO records VALUES ('gmail_cursor',?,?)",
                (
                    email_service.expected_email,
                    json.dumps(
                        {"updated_at": (at + timedelta(seconds=seconds)).isoformat()}
                    ),
                ),
            )
        assert (
            check(
                pilot.readiness(email_service.expected_email, at=at),
                "Recent reply sync",
            )["status"]
            == "action"
        )


def test_preview_and_readiness_do_not_call_writers_or_providers(monkeypatch):
    c = create()
    from services.llm_factory import llm_factory

    writer = Mock(side_effect=AssertionError("Read-only endpoints cannot write"))
    provider = AsyncMock(
        side_effect=AssertionError("Read-only endpoints cannot contact providers")
    )
    monkeypatch.setattr(store, "put", writer)
    monkeypatch.setattr(store, "queue_approval", writer)
    monkeypatch.setattr(campaigns, "_reserve_slot", writer)
    monkeypatch.setattr(email_service, "get_profile", provider)
    monkeypatch.setattr(email_service, "send_email", provider)
    monkeypatch.setattr(llm_factory, "invoke_drafter", provider)
    before = ledger()
    pilot.dry_run(c["id"], email_service.expected_email)
    pilot.readiness(email_service.expected_email)
    assert ledger() == before
    writer.assert_not_called()
    provider.assert_not_awaited()


def test_api_auth_read_only_results_and_mailbox_scoping(api, monkeypatch):
    c = create()
    path = f"/api/campaigns/{c['id']}/dry-run"
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.get(path).status_code == 401
    assert api.get("/api/pilot/readiness").status_code == 401
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    before = ledger()
    assert api.get(path).json()["read_only"]
    assert api.get("/api/pilot/readiness").json()["read_only"]
    assert ledger() == before
    monkeypatch.setattr(email_service, "expected_email", "other@example.test")
    assert api.get(path).status_code == 404
    assert api.get("/api/campaigns/missing/dry-run").status_code == 404


@pytest.mark.parametrize(
    "change", [{"status": "delivery_unknown"}, {"provider_message_id": ""}]
)
def test_unconfirmed_submission_cannot_prove_a_completed_test_cycle(change):
    store.put(
        "messages",
        "test",
        {
            "from": email_service.expected_email,
            "to": "owned@example.test",
            "purpose": "test",
            "status": "sent",
            "provider_message_id": "provider-test",
            "thread_id": "thread-test",
            **change,
        },
    )
    at = datetime.now(timezone.utc) + timedelta(seconds=2)
    store.put(
        "inbox",
        "incoming",
        {
            "mailbox": email_service.expected_email,
            "sender": "owned@example.test",
            "thread_id": "thread-test",
            "matched_outbound_id": "test",
            "provider_timestamp": str(
                int((at - timedelta(seconds=1)).timestamp() * 1000)
            ),
        },
    )
    assert (
        check(
            pilot.readiness(email_service.expected_email, at=at),
            "Owned-mailbox send and reply evidence",
        )["status"]
        == "action"
    )
