"""Opt-in daily local follow-up drafts. No Gmail, research, model or send calls."""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from config import settings
from core.store import store, now, ConflictError
from services import followups
from services.campaigns import CampaignRunner, _read, _write, next_time
from services.contacts import EligibilityError
from services.email_service import email_service
from services.report_service import TZ, instant

KIND = "followup_schedules"
RUNS = "followup_schedule_runs"
LEASE = "followup-draft-scheduler"
DEFAULT = {
    "version": 0,
    "paused": True,
    "local_time": "09:00",
    "weekdays_only": True,
    "batch_size": 1,
    "next_run_at": None,
}


class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=0)
    paused: bool
    local_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    weekdays_only: bool = True
    batch_size: int = Field(ge=1, le=3)


def config(mailbox):
    return store.get(KIND, mailbox or "") or {**DEFAULT, "id": mailbox or ""}


def update(payload, mailbox):
    if not mailbox:
        raise EligibilityError("Connect Gmail before enabling follow-up drafting")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            previous = _read(db, KIND, mailbox)
        except KeyError:
            previous = DEFAULT
        if previous["version"] != payload.version:
            raise ConflictError("Follow-up schedule changed; refresh before saving")
        value = {
            **payload.model_dump(),
            "id": mailbox,
            "version": payload.version + 1,
            "next_run_at": None,
        }
        if not value["paused"]:
            day = datetime.now(TZ).date()
            claimed = db.execute(
                "SELECT 1 FROM records WHERE kind=? AND id=?",
                (RUNS, f"{mailbox}:{day}"),
            ).fetchone()
            value["next_run_at"] = next_time(
                value, datetime.now(TZ), tomorrow=bool(claimed)
            )
        _write(db, KIND, value)
    store.event("followups.schedule_changed", mailbox, payload.model_dump())
    return value


def sync_fresh(mailbox, at):
    cursor = store.get("gmail_cursor", mailbox or "") or {}
    synced = instant(cursor.get("updated_at"))
    return bool(synced and 0 <= (at - synced).total_seconds() <= 900)


def listing(mailbox):
    current = config(mailbox)
    candidates = followups.list_candidates(mailbox)["candidates"]
    eligible = [c for c in candidates if c["eligible"]]
    runs = [r for r in store.list(RUNS) if r["mailbox"] == mailbox]
    return {
        "config": current,
        "runs": list(reversed(runs))[:14],
        "eligible_count": len(eligible),
        "next_candidates": eligible[: current["batch_size"]],
        "fresh_sync": sync_fresh(mailbox, datetime.now(timezone.utc)),
        "worker_enabled": settings.FOLLOWUP_SCHEDULES_ENABLED,
        "automatic_sending": False,
        "timezone": str(TZ),
        "daily_maximum": 3,
    }


def _finish(run_id, status, *, pause=False):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        run = _read(db, RUNS, run_id)
        run.update(status=status, finished_at=now())
        _write(db, RUNS, run)
        if pause:
            current = _read(db, KIND, run["mailbox"])
            current.update(
                paused=True, next_run_at=None, version=current["version"] + 1
            )
            _write(db, KIND, current)
    return run


def _recover():
    # Called only while holding the scheduler lease. Never replay a partial batch.
    for run in store.list(RUNS):
        if run["status"] == "running":
            _finish(run["id"], "interrupted", pause=True)


def run_batch(mailbox, *, manual=False, stop=lambda: False):
    if not mailbox:
        return None
    owner = uuid4().hex
    try:
        store.acquire_lease(LEASE, owner, seconds=300)
    except ConflictError:
        raise ConflictError("Follow-up drafting is already running")
    run = None
    try:
        _recover()
        at = datetime.now(timezone.utc)
        current = config(mailbox)
        if current["paused"]:
            if manual:
                raise ConflictError(
                    "Enable the follow-up schedule before preparing a batch"
                )
            return None
        if not manual and (
            not current["next_run_at"]
            or instant(current["next_run_at"]) > at
            or (current["weekdays_only"] and at.astimezone(TZ).weekday() >= 5)
        ):
            return None
        if not sync_fresh(mailbox, at):
            if manual:
                raise EligibilityError("Sync Gmail within 15 minutes before drafting")
            return None
        candidates = [
            c["id"]
            for c in followups.list_candidates(mailbox)["candidates"]
            if c["eligible"]
        ][: current["batch_size"]]
        if not candidates:
            return None
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            saved = _read(db, KIND, mailbox)
            if saved["version"] != current["version"] or saved["paused"]:
                raise ConflictError("Follow-up schedule changed before the batch")
            run_id = f"{mailbox}:{at.astimezone(TZ).date()}"
            if db.execute(
                "SELECT 1 FROM records WHERE kind=? AND id=?", (RUNS, run_id)
            ).fetchone():
                if manual:
                    raise ConflictError(
                        "This mailbox already claimed its daily follow-up batch"
                    )
                return None
            run = {
                "id": run_id,
                "mailbox": mailbox,
                "status": "running",
                "manual": manual,
                "outbound_ids": candidates,
                "results": [],
                "created_at": now(),
            }
            _write(db, RUNS, run)
            saved["next_run_at"] = next_time(saved, at, tomorrow=True)
            _write(db, KIND, saved)
        for outbound_id in candidates:
            store.renew_lease(LEASE, owner)
            latest = config(mailbox)
            if stop() or latest["paused"] or latest["version"] != current["version"]:
                return _finish(run["id"], "stopped")
            # Do not let a batch spanning SAST midnight consume the next day's work.
            if datetime.now(TZ).date() != at.astimezone(TZ).date():
                return _finish(run["id"], "stopped")
            try:
                preview = followups.preview(outbound_id, mailbox)
                approval = followups.queue(
                    outbound_id, mailbox, preview["id"], preview["body"]
                )
                result = {
                    "outbound_id": outbound_id,
                    "decision": "queued",
                    "approval_id": approval["id"],
                }
            except (ValueError, KeyError) as exc:
                result = {
                    "outbound_id": outbound_id,
                    "decision": "skipped",
                    "reason": (
                        str(exc)
                        if not isinstance(exc, KeyError)
                        else "Original outreach is unavailable"
                    ),
                }
            run["results"].append(result)
            store.put(RUNS, run["id"], run)
        return _finish(run["id"], "completed")
    except BaseException:
        if run:
            _finish(run["id"], "failed", pause=True)
        raise
    finally:
        store.release_lease(LEASE, owner)


def run_due(stop=lambda: False):
    # Recovery is needed even when the configured mailbox has changed or is absent.
    owner = uuid4().hex
    try:
        store.acquire_lease(LEASE, owner, seconds=300)
    except ConflictError:
        return False
    try:
        _recover()
    finally:
        store.release_lease(LEASE, owner)
    return run_batch(email_service.expected_email, stop=stop)


followup_schedule_runner = CampaignRunner(run_due)
