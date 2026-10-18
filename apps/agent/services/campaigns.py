"""Bounded local campaign drafting. This service never dispatches email."""

import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime, timedelta
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from core.store import store, now, ConflictError
from services.contacts import EligibilityError
from services.email_service import email_service
from services.lead_service import ensure_qualified, draft_lead
from services.proposals import create_preview
from services.report_service import TZ, instant

logger = logging.getLogger("agent.campaigns")
DAILY_DRAFT_LIMIT = 10
LEASE = "campaign-draft-runner"


class CampaignInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    lead_ids: list[str] = Field(min_length=1, max_length=20)
    local_time: str = Field(default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    weekdays_only: bool = True
    batch_size: int = Field(default=3, ge=1, le=5)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip() or "\n" in value or "\r" in value:
            raise ValueError("Provide a single-line campaign name")
        return value.strip()

    @field_validator("lead_ids")
    @classmethod
    def unique_leads(cls, value):
        if len(set(value)) != len(value) or any(
            not item or len(item) > 100 for item in value
        ):
            raise ValueError("Select unique saved lead IDs")
        return value


def next_time(campaign, at, *, tomorrow=False):
    local = at.astimezone(TZ)
    hour, minute = map(int, campaign["local_time"].split(":"))
    candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if tomorrow or candidate <= local:
        candidate += timedelta(days=1)
    while campaign["weekdays_only"] and candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def _read(db, kind, record_id):
    row = db.execute(
        "SELECT data FROM records WHERE kind=? AND id=?", (kind, record_id)
    ).fetchone()
    if not row:
        raise KeyError(record_id)
    return json.loads(row[0])


def _write(db, kind, value):
    value["updated_at"] = now()
    db.execute(
        "INSERT INTO records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
        (kind, value["id"], json.dumps(value)),
    )


def create(payload, mailbox):
    if not mailbox:
        raise EligibilityError("Connect Gmail before creating a campaign")
    for lead_id in payload.lead_ids:
        ensure_qualified(lead_id)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT data FROM records WHERE kind='campaigns'"
            ).fetchall()
        ]
        if (
            sum(
                c["mailbox"] == mailbox and c["status"] in ("paused", "active")
                for c in existing
            )
            >= 5
        ):
            raise ValueError(
                "Keep at most five unfinished campaigns; complete or cancel one first"
            )
        value = {
            **payload.model_dump(),
            "id": uuid4().hex,
            "mailbox": mailbox,
            "version": 0,
            "status": "paused",
            "cursor": 0,
            "next_run_at": None,
            "created_at": now(),
        }
        _write(db, "campaigns", value)
    return value


def control(record_id, mailbox, action, version):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        value = _read(db, "campaigns", record_id)
        if value["mailbox"] != mailbox:
            raise KeyError(record_id)
        if value["version"] != version or value["status"] not in ("active", "paused"):
            raise ConflictError("Campaign changed or is finished; refresh its state")
        if action not in ("pause", "resume", "cancel"):
            raise ValueError("Unsupported campaign action")
        value.update(
            status={"pause": "paused", "resume": "active", "cancel": "cancelled"}[
                action
            ],
            version=version + 1,
        )
        at = datetime.now(TZ)
        already_ran = db.execute(
            "SELECT 1 FROM records WHERE kind='campaign_runs' AND id=?",
            (f"{record_id}:{at.date()}",),
        ).fetchone()
        value["next_run_at"] = (
            next_time(value, at, tomorrow=bool(already_ran))
            if action == "resume"
            else None
        )
        _write(db, "campaigns", value)
    return value


def usage(at=None):
    day = str((at or datetime.now(TZ)).astimezone(TZ).date())
    used = sum(slot["day"] == day for slot in store.list("campaign_draft_slots"))
    return {
        "day": day,
        "used": used,
        "limit": DAILY_DRAFT_LIMIT,
        "remaining": max(0, DAILY_DRAFT_LIMIT - used),
    }


def listing(mailbox):
    return {
        "campaigns": [
            c for c in reversed(store.list("campaigns")) if c["mailbox"] == mailbox
        ],
        "runs": [
            r for r in reversed(store.list("campaign_runs")) if r["mailbox"] == mailbox
        ][:30],
        "draft_budget": usage(),
        "timezone": str(TZ),
        "automatic_sending": False,
    }


def _claim(record_id, mailbox, at, manual):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        c = _read(db, "campaigns", record_id)
        if c["mailbox"] != mailbox:
            raise KeyError(record_id)
        if c["status"] != "active":
            raise ConflictError("Resume this campaign before running it")
        if not manual and (not c["next_run_at"] or instant(c["next_run_at"]) > at):
            return None
        if not manual and c["weekdays_only"] and at.astimezone(TZ).weekday() >= 5:
            c["next_run_at"] = next_time(c, at)
            _write(db, "campaigns", c)
            return None
        day = str(at.astimezone(TZ).date())
        run_id = f"{record_id}:{day}"
        if db.execute(
            "SELECT 1 FROM records WHERE kind='campaign_runs' AND id=?", (run_id,)
        ).fetchone():
            raise ConflictError(
                "This campaign already ran today; the next batch is on its next scheduled day"
            )
        run = {
            "id": run_id,
            "campaign_id": record_id,
            "mailbox": mailbox,
            "status": "running",
            "day": day,
            "manual": manual,
            "results": [],
            "created_at": now(),
        }
        _write(db, "campaign_runs", run)
        c.update(last_run_id=run_id, next_run_at=next_time(c, at, tomorrow=True))
        _write(db, "campaigns", c)
    return run


def _reserve_slot(run, lead_id, at=None):
    day = str((at or datetime.now(TZ)).astimezone(TZ).date())
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        slots = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT data FROM records WHERE kind='campaign_draft_slots'"
            ).fetchall()
        ]
        if sum(s["day"] == day for s in slots) >= DAILY_DRAFT_LIMIT:
            return False
        _write(
            db,
            "campaign_draft_slots",
            {
                "id": f"{run['id']}:{lead_id}",
                "day": day,
                "run_id": run["id"],
                "lead_id": lead_id,
                "created_at": now(),
            },
        )
    return True


def _finish(run_id, status, *, pause=False):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        run = _read(db, "campaign_runs", run_id)
        run["status"] = status
        _write(db, "campaign_runs", run)
        c = _read(db, "campaigns", run["campaign_id"])
        if c["cursor"] >= len(c["lead_ids"]) and c["status"] != "cancelled":
            c.update(status="completed", next_run_at=None, version=c["version"] + 1)
        elif pause and c["status"] == "active":
            c.update(status="paused", next_run_at=None, version=c["version"] + 1)
        _write(db, "campaigns", c)
    return run


def _recover():
    for run in store.list("campaign_runs"):
        if run["status"] == "running":
            _finish(run["id"], "interrupted", pause=True)


def run_campaign(record_id, mailbox, *, manual=True, at=None, stop=lambda: False):
    fixed_at = at
    owner = uuid4().hex
    try:
        store.acquire_lease(LEASE, owner, seconds=120)
    except ConflictError as exc:
        raise ConflictError(
            "Another campaign batch is running; retry after it finishes"
        ) from exc
    run = None
    try:
        _recover()  # An abandoned local batch is paused, never blindly replayed.
        at = at or datetime.now(TZ)
        run = _claim(record_id, mailbox, at, manual)
        if not run:
            return None
        c = store.get("campaigns", record_id)
        for _ in range(c["batch_size"]):
            store.renew_lease(LEASE, owner)
            c = store.get("campaigns", record_id)
            if stop():
                return _finish(run["id"], "interrupted", pause=True)
            if c["status"] != "active":
                return _finish(run["id"], "paused")
            if c["cursor"] >= len(c["lead_ids"]):
                break
            lead_id = c["lead_ids"][c["cursor"]]
            if not _reserve_slot(run, lead_id, fixed_at):
                return _finish(run["id"], "daily_budget_reached")
            try:
                preview = create_preview(lead_id, mailbox)
                approval = draft_lead(
                    lead_id,
                    preview["subject"],
                    preview["body"],
                    mailbox,
                    preview["id"],
                    {"id": c["id"], "name": c["name"], "run_id": run["id"]},
                )
                decision = (
                    "queued"
                    if (approval.get("proposal_snapshot") or {}).get("id")
                    == preview["id"]
                    else "existing_approval"
                )
                result = {
                    "lead_id": lead_id,
                    "decision": decision,
                    "approval_id": approval["id"],
                    "approval_status": approval["status"],
                }
            except (ValueError, KeyError) as exc:
                result = {
                    "lead_id": lead_id,
                    "decision": "skipped",
                    "reason": (
                        str(exc)
                        if not isinstance(exc, KeyError)
                        else "Saved lead no longer exists"
                    ),
                }
            with store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                current = _read(db, "campaigns", record_id)
                saved_run = _read(db, "campaign_runs", run["id"])
                if current["cursor"] != c["cursor"] or saved_run["status"] != "running":
                    raise ConflictError("Campaign progress changed during drafting")
                current["cursor"] += 1
                saved_run["results"].append(result)
                _write(db, "campaigns", current)
                _write(db, "campaign_runs", saved_run)
        return _finish(run["id"], "completed")
    except BaseException:
        if (
            run
            and (store.get("campaign_runs", run["id"]) or {}).get("status") == "running"
        ):
            _finish(run["id"], "failed", pause=True)
        raise
    finally:
        store.release_lease(LEASE, owner)


def run_due(stop=lambda: False):
    # Also recover after restart when no active campaign is due.
    owner = uuid4().hex
    try:
        store.acquire_lease(LEASE, owner, seconds=120)
    except ConflictError:
        return False
    try:
        _recover()
    finally:
        store.release_lease(LEASE, owner)
    for c in sorted(store.list("campaigns"), key=lambda c: c.get("next_run_at") or "~"):
        if (
            c["mailbox"] == email_service.expected_email
            and c["status"] == "active"
            and c.get("next_run_at")
            and instant(c["next_run_at"]) <= datetime.now(TZ)
        ):
            try:
                run_campaign(c["id"], c["mailbox"], manual=False, stop=stop)
            except ConflictError:
                return False
            return True
    return False


class CampaignRunner:
    def __init__(self):
        self.task = None
        self.stopping = None

    def start(self):
        if not self.task or self.task.done():
            self.stopping = asyncio.Event()
            self.task = asyncio.create_task(self.loop())

    async def loop(self):
        while not self.stopping.is_set():
            try:
                await asyncio.to_thread(run_due, self.stopping.is_set)
            except Exception as exc:
                logger.warning("Campaign draft tick failed (%s)", type(exc).__name__)
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self.stopping.wait(), timeout=30)

    async def stop(self):
        if self.task:
            self.stopping.set()
            await self.task
            self.task = None


campaign_runner = CampaignRunner()
