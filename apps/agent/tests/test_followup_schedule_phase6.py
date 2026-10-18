"""Local opt-in follow-up draft batches; no real providers or email."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from config import settings
from core.store import store, ConflictError
from services import followup_schedule as schedule, followups
from services.contacts import EligibilityError, suppress
from services.email_service import email_service
from services.report_service import TZ
from test_followups_phase5 import original, raw_record


def enable(**changes):
    return schedule.update(
        schedule.ScheduleInput(
            **{
                "version": schedule.config(email_service.expected_email)["version"],
                "paused": False,
                "local_time": "09:00",
                "weekdays_only": True,
                "batch_size": 1,
                **changes,
            }
        ),
        email_service.expected_email,
    )


def seed(count=1):
    message, lead = original()
    for i in range(1, count):
        raw_record(
            "messages",
            f"initial-{i}",
            {
                **message,
                "thread_id": f"thread-{i + 1}",
                "provider_message_id": f"provider-{i}",
            },
        )
    store.put(
        "gmail_cursor",
        email_service.expected_email,
        {"thread_ids": [f"thread-{i + 1}" for i in range(count)]},
    )
    return message, lead


def due():
    value = schedule.config(email_service.expected_email)
    store.put(
        schedule.KIND,
        email_service.expected_email,
        {
            **value,
            "next_run_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "weekdays_only": False,
        },
    )


def test_default_and_listing_make_no_records_or_provider_calls(monkeypatch):
    monkeypatch.setattr(
        email_service,
        "_configure",
        lambda: pytest.fail("Provider configuration attempted"),
    )
    assert schedule.listing(email_service.expected_email)["config"]["paused"]
    assert schedule.run_due() is None
    assert store.list(schedule.KIND) == []
    assert store.list(schedule.RUNS) == []
    assert store.list("approvals") == []


def test_batch_bound_threaded_approval_only_and_once_per_day(monkeypatch):
    seed(5)
    enable(batch_size=3)
    monkeypatch.setattr(
        email_service, "send_email", lambda *a, **kw: pytest.fail("Email sent")
    )
    result = schedule.run_batch(email_service.expected_email, manual=True)
    assert result["status"] == "completed"
    assert len(result["results"]) == 3
    assert all(row["decision"] == "queued" for row in result["results"])
    assert len(store.list("messages")) == 5
    approvals = [a for a in store.list("approvals") if a.get("followup_of")]
    assert len(approvals) == 3
    assert all(a["status"] == "pending" and a["in_reply_to"] for a in approvals)
    with pytest.raises(ConflictError, match="daily"):
        schedule.run_batch(email_service.expected_email, manual=True)
    assert len(store.list(schedule.RUNS)) == 1


@pytest.mark.parametrize("age", [16, -1])
def test_stale_or_future_sync_waits_without_claiming_and_retries_after_sync(age):
    seed()
    enable()
    due()
    raw_record(
        "gmail_cursor",
        email_service.expected_email,
        {
            "thread_ids": ["thread-1"],
            "updated_at": (
                datetime.now(timezone.utc) - timedelta(minutes=age)
            ).isoformat(),
        },
    )
    assert schedule.run_due() is None
    assert store.list(schedule.RUNS) == []
    with pytest.raises(EligibilityError, match="Sync Gmail"):
        schedule.run_batch(email_service.expected_email, manual=True)
    store.put(
        "gmail_cursor", email_service.expected_email, {"thread_ids": ["thread-1"]}
    )
    assert schedule.run_due()["status"] == "completed"


@pytest.mark.parametrize(
    "block",
    [
        "reply",
        "bounce",
        "suppressed",
        "test",
        "unconfirmed",
        "outcome",
        "missing_thread_sync",
        "existing_rejected",
    ],
)
def test_existing_followup_guards_are_not_bypassed(block):
    message, _ = seed()
    enable()
    if block in ("reply", "bounce"):
        store.put(
            "inbox",
            "incoming",
            {
                "mailbox": email_service.expected_email,
                "thread_id": "thread-1",
                "bounce": block == "bounce",
            },
        )
    elif block == "suppressed":
        suppress(message["to"], "No more contact")
    elif block == "test":
        raw_record("messages", message["id"], {**message, "purpose": "test"})
    elif block == "unconfirmed":
        raw_record("messages", message["id"], {**message, "provider_message_id": None})
    elif block == "outcome":
        store.put(
            "outcomes",
            "outcome",
            {
                "mailbox": email_service.expected_email,
                "thread_id": "thread-1",
                "outcome": "declined",
            },
        )
    elif block == "missing_thread_sync":
        store.put("gmail_cursor", email_service.expected_email, {"thread_ids": []})
    else:
        store.put(
            "approvals",
            followups.approval_key(email_service.expected_email, "thread-1"),
            {"status": "rejected"},
        )
    assert schedule.run_batch(email_service.expected_email, manual=True) is None
    assert store.list(schedule.RUNS) == []


def test_pause_disable_account_and_version_guards():
    seed()
    with pytest.raises(ConflictError, match="Enable"):
        schedule.run_batch(email_service.expected_email, manual=True)
    value = enable()
    with pytest.raises(ConflictError, match="changed"):
        enable(version=0)
    assert schedule.config("another@example.test")["paused"]
    enable(paused=True)
    assert schedule.run_due() is None
    assert schedule.config(email_service.expected_email)["version"] > value["version"]
    with pytest.raises(EligibilityError):
        schedule.update(
            schedule.ScheduleInput(
                version=0, paused=False, local_time="09:00", batch_size=1
            ),
            None,
        )


def test_pause_between_members_stops_remaining_work(monkeypatch):
    seed(3)
    enable(batch_size=3)
    queue = followups.queue

    def pause_after_first(*args):
        result = queue(*args)
        enable(paused=True)
        return result

    monkeypatch.setattr(followups, "queue", pause_after_first)
    result = schedule.run_batch(email_service.expected_email, manual=True)
    assert result["status"] == "stopped"
    assert len(result["results"]) == 1


def test_eligibility_change_at_queue_is_skipped(monkeypatch):
    message, _ = seed()
    enable()
    preview = followups.preview

    def changed(*args):
        result = preview(*args)
        suppress(message["to"], "Opt-out arrived")
        return result

    monkeypatch.setattr(followups, "preview", changed)
    result = schedule.run_batch(email_service.expected_email, manual=True)
    assert result["results"][0]["decision"] == "skipped"
    assert len(store.list("approvals")) == 1


def test_failure_after_queue_pauses_and_restart_does_not_duplicate(monkeypatch):
    seed(3)
    enable(batch_size=3)
    queue = followups.queue

    def crash(*args):
        queue(*args)
        raise RuntimeError("Simulated crash after approval persisted")

    monkeypatch.setattr(followups, "queue", crash)
    with pytest.raises(RuntimeError):
        schedule.run_batch(email_service.expected_email, manual=True)
    assert schedule.config(email_service.expected_email)["paused"]
    run = store.list(schedule.RUNS)[0]
    assert run["status"] == "failed"
    assert len([a for a in store.list("approvals") if a.get("followup_of")]) == 1
    # Simulate a process dying before its finally/error handlers.
    store.put(schedule.RUNS, run["id"], {**run, "status": "running"})
    enable()
    assert schedule.run_due() is None
    assert store.get(schedule.RUNS, run["id"])["status"] == "interrupted"
    assert schedule.config(email_service.expected_email)["paused"]


def test_concurrent_batches_claim_once():
    seed(4)
    enable(batch_size=3)

    def attempt(_):
        try:
            return schedule.run_batch(email_service.expected_email, manual=True)
        except ConflictError:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert sum(r is not None for r in results) == 1
    assert len(store.list(schedule.RUNS)) == 1
    assert len([a for a in store.list("approvals") if a.get("followup_of")]) == 3


def test_due_time_weekday_and_no_catchup_replay():
    seed(3)
    enable()
    assert schedule.run_due() is None  # First scheduled time is in the future.
    due()
    assert schedule.run_due()["status"] == "completed"
    assert schedule.run_due() is None
    next_at = datetime.fromisoformat(
        schedule.config(email_service.expected_email)["next_run_at"]
    )
    assert next_at.astimezone(TZ).date() == datetime.now(TZ).date() + timedelta(days=1)
    assert len(store.list(schedule.RUNS)) == 1


def test_stop_flag_preserves_claim_without_queueing():
    seed()
    enable()
    result = schedule.run_batch(
        email_service.expected_email, manual=True, stop=lambda: True
    )
    assert result["status"] == "stopped"
    assert result["results"] == []
    assert len(store.list("approvals")) == 1


def test_weekday_schedule_waits_on_weekend_even_if_overdue(monkeypatch):
    seed()
    enable()
    current = schedule.config(email_service.expected_email)
    weekend = datetime(2026, 10, 17, 10, tzinfo=TZ)
    store.put(
        schedule.KIND,
        email_service.expected_email,
        {
            **current,
            "next_run_at": (weekend - timedelta(days=2)).isoformat(),
        },
    )

    class Saturday(datetime):
        @classmethod
        def now(cls, tz=None):
            return weekend.astimezone(tz or timezone.utc)

    monkeypatch.setattr(schedule, "datetime", Saturday)
    assert schedule.run_due() is None
    assert store.list(schedule.RUNS) == []


def test_batch_stops_if_sast_date_changes_after_claim(monkeypatch):
    seed()
    enable()
    at = datetime.now(timezone.utc)

    class CrossingMidnight(datetime):
        @classmethod
        def now(cls, tz=None):
            return (at + timedelta(days=1)).astimezone(TZ) if tz == TZ else at

    monkeypatch.setattr(schedule, "datetime", CrossingMidnight)
    result = schedule.run_batch(email_service.expected_email, manual=True)
    assert result["status"] == "stopped"
    assert result["results"] == []
    assert len(store.list("approvals")) == 1


def test_api_auth_strict_input_and_mailbox_isolation(monkeypatch):
    from main import app

    with TestClient(app) as api:
        monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
        assert api.get("/api/followups/schedule").status_code == 401
        assert api.post("/api/followups/schedule/run").status_code == 401
        monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
        payload = {
            "version": 0,
            "paused": False,
            "local_time": "09:00",
            "weekdays_only": True,
            "batch_size": 1,
        }
        for changes in ({"batch_size": 4}, {"local_time": "25:00"}, {"send": True}):
            assert (
                api.patch(
                    "/api/followups/schedule", json={**payload, **changes}
                ).status_code
                == 422
            )
        assert api.patch("/api/followups/schedule", json=payload).status_code == 200
        assert api.patch("/api/followups/schedule", json=payload).status_code == 409
        monkeypatch.setattr(email_service, "expected_email", "other@example.test")
        result = api.get("/api/followups/schedule").json()
        assert result["config"]["paused"] and result["runs"] == []
