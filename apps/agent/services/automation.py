"""Single opt-in coordinator. Outgoing email always stays behind approval."""

import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from config import settings
from core.store import store, now, ConflictError
from services import followups, research_jobs
from services.campaigns import _read, _write
from services.email_service import email_service
from services.inbox_service import process_inbox_batch
from services.lead_discovery import DiscoveryUnavailable
from services.lead_service import ensure_qualified, initial_outreach_state, draft_lead
from services.proposals import create_preview
from services.reply_service import (
    assess_reply,
    fingerprint,
    reply_context,
    reply_preview,
    queue_reply,
)
from services.report_service import TZ, instant, generate_weekly_report, queue_report

logger = logging.getLogger(__name__)
LEASE = "approval-only-automation"
DEFAULT = {
    "version": 0,
    "paused": True,
    "location": "",
    "industry": "",
    "research_enabled": False,
    "research_results": 2,
    "research_requests": 3,
    "daily_draft_limit": 3,
    "local_time": "09:00",
    "weekdays_only": True,
    "weekly_report_email": True,
}


class AutomationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=0)
    paused: bool
    location: str = Field(default="", max_length=200)
    industry: str = Field(default="", max_length=200)
    research_enabled: bool = False
    research_results: int = Field(default=2, ge=1, le=5)
    research_requests: int = Field(default=3, ge=1, le=5)
    daily_draft_limit: int = Field(default=3, ge=1, le=10)
    local_time: str = Field(default="09:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    weekdays_only: bool = True
    weekly_report_email: bool = True

    @model_validator(mode="after")
    def target(self):
        self.location = self.location.strip()
        self.industry = self.industry.strip()
        if self.research_enabled and (not self.location or not self.industry):
            raise ValueError(
                "Set a target town and business type for automatic research"
            )
        return self


def config(mailbox):
    return store.get("automation_config", mailbox or "") or {
        **DEFAULT,
        "id": mailbox or "",
    }


def research_prefix(mailbox):
    return "automation_" + sha256(mailbox.encode()).hexdigest()[:16] + "_"


def update(payload, mailbox):
    if not mailbox:
        raise ValueError("Connect Gmail locally before enabling automation")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            previous = _read(db, "automation_config", mailbox)
        except KeyError:
            previous = DEFAULT
        if previous["version"] != payload.version:
            raise ConflictError("Automation settings changed; refresh before saving")
        value = {**payload.model_dump(), "id": mailbox, "version": payload.version + 1}
        _write(db, "automation_config", value)
        db.execute(
            "INSERT INTO activity VALUES (?,?,?,?,?)",
            (
                uuid4().hex,
                "automation.settings_changed",
                mailbox,
                now(),
                json.dumps(payload.model_dump()),
            ),
        )
    if payload.paused:
        for job in store.list("research_jobs"):
            if (
                job["id"].startswith(research_prefix(mailbox))
                and job["status"] in research_jobs.ACTIVE
            ):
                research_jobs.control_job(job["id"], "pause")
    return value


def usage(mailbox, at=None):
    day = str((at or datetime.now(TZ)).astimezone(TZ).date())
    slots = [
        s
        for s in store.list("automation_draft_slots")
        if s["mailbox"] == mailbox and s["day"] == day
    ]
    limit = config(mailbox)["daily_draft_limit"]
    return {
        "day": day,
        "used": len(slots),
        "limit": limit,
        "remaining": max(0, limit - len(slots)),
    }


def listing(mailbox):
    return {
        "config": config(mailbox),
        "budget": usage(mailbox),
        "runtime": store.get("automation_runtime", mailbox or ""),
        "runs": [
            r
            for r in reversed(store.list("automation_runs"))
            if r["mailbox"] == mailbox
        ][:15],
        "worker_enabled": settings.AUTOMATION_ENABLED,
        "automatic_sending": False,
        "warning": "Automation prepares eligible work only. Missing identity/activity/website evidence or recorded contact permission is never invented: those candidates are skipped. Pausing this mode does not disable separately activated legacy schedules or revoke saved approvals.",
    }


def _reserve(mailbox, kind, target, expected_version):
    at = datetime.now(TZ)
    day = str(at.date())
    key = sha256(f"{mailbox}:{day}:{kind}:{target}".encode()).hexdigest()
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = _read(db, "automation_config", mailbox)
        if current["paused"] or current["version"] != expected_version:
            return False
        slots = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT data FROM records WHERE kind='automation_draft_slots'"
            )
        ]
        if (
            any(s["id"] == key for s in slots)
            or sum(s["mailbox"] == mailbox and s["day"] == day for s in slots)
            >= current["daily_draft_limit"]
        ):
            return False
        _write(
            db,
            "automation_draft_slots",
            {"id": key, "mailbox": mailbox, "day": day, "kind": kind, "target": target},
        )
    return True


def _active(mailbox, saved, stop):
    current = config(mailbox)
    return (
        not stop()
        and email_service.expected_email == mailbox
        and not current["paused"]
        and current["version"] == saved["version"]
    )


def _window(saved, at):
    local = at.astimezone(TZ)
    return (not saved["weekdays_only"] or local.weekday() < 5) and local.strftime(
        "%H:%M"
    ) >= saved["local_time"]


def _draft(mailbox, saved, run, kind, target, call):
    if not _reserve(mailbox, kind, target, saved["version"]):
        return
    try:
        approval = call()
        run["results"].append(
            {
                "stage": kind,
                "target": target,
                "status": "awaiting_approval",
                "approval_id": approval["id"],
            }
        )
    except (ValueError, KeyError) as exc:
        run["results"].append(
            {
                "stage": kind,
                "target": target,
                "status": "skipped",
                "reason": str(exc)[:400],
            }
        )
    store.put("automation_runs", run["id"], run)


def _replies(mailbox, saved, run, stop):
    for mail in reversed(store.list("inbox")):
        if not _active(mailbox, saved, stop):
            return
        if mail.get("mailbox") != mailbox or mail.get("conversation_purpose") == "test":
            continue
        try:
            _, original = reply_context(mail["id"], mailbox)
        except (ValueError, KeyError):
            continue
        if original.get("purpose") == "test":
            continue
        assessment = assess_reply(mail)
        key = sha256(f"{mailbox}:{mail['id']}".encode()).hexdigest()
        previous = store.get("automation_reply_assessments", key)
        if not previous or previous["fingerprint"] != fingerprint(mail):
            store.put(
                "automation_reply_assessments",
                key,
                {"mailbox": mailbox, "incoming_id": mail["id"], **assessment},
            )
        if not assessment["template_available"] or store.get(
            "approvals", "reply_" + mail["id"]
        ):
            continue

        def prepare():
            preview = reply_preview(mail["id"], mailbox)
            return queue_reply(mail["id"], preview["body"], mailbox, preview["id"])

        _draft(mailbox, saved, run, "reply", mail["id"], prepare)


def _initial(mailbox, saved, run, stop):
    exceptions = []
    for candidate in store.list("leads"):
        if not _active(mailbox, saved, stop):
            return
        # Target labels constrain new initial drafts; empty labels allow all saved leads.
        location = " ".join(saved["location"].casefold().split())
        candidate_location = " ".join(candidate.get("location", "").casefold().split())
        industry = saved["industry"].strip().casefold()
        if location and location != candidate_location:
            continue
        if industry and industry not in candidate.get("industry", "").casefold():
            continue
        try:
            lead = ensure_qualified(candidate["id"])
            _, existing = initial_outreach_state(lead, mailbox)
            if existing:
                continue
        except (ValueError, KeyError) as exc:
            if len(exceptions) < 20:
                exceptions.append(
                    {
                        "lead_id": candidate["id"],
                        "name": candidate.get("name", ""),
                        "reason": str(exc)[:400],
                    }
                )
            continue

        def prepare():
            preview = create_preview(lead["id"], mailbox)
            return draft_lead(
                lead["id"],
                preview["subject"],
                preview["body"],
                mailbox,
                preview["id"],
                {"id": "automation", "name": "Automation mode", "run_id": run["id"]},
            )

        _draft(mailbox, saved, run, "initial", lead["id"], prepare)
    run["lead_exceptions"] = exceptions


def _followups(mailbox, saved, run, stop):
    for candidate in followups.list_candidates(mailbox)["candidates"]:
        if not _active(mailbox, saved, stop):
            return
        if not candidate["eligible"]:
            continue

        def prepare():
            preview = followups.preview(candidate["id"], mailbox)
            return followups.queue(
                candidate["id"], mailbox, preview["id"], preview["body"]
            )

        _draft(mailbox, saved, run, "followup", candidate["id"], prepare)


async def tick(stop=lambda: False):
    mailbox = email_service.expected_email
    if not mailbox or config(mailbox)["paused"]:
        return None
    owner = uuid4().hex
    try:
        store.acquire_lease(LEASE, owner, seconds=600)
    except ConflictError:
        return None
    run = None
    heartbeat = None
    lease_lost = asyncio.Event()
    external_stop = stop

    def stopped():
        return external_stop() or lease_lost.is_set()

    stop = stopped
    try:
        saved = config(mailbox)
        if not _active(mailbox, saved, stop):
            return None
        # No automatic replay after an interrupted provider/local step.
        interrupted = [
            r for r in store.list("automation_runs") if r["status"] == "running"
        ]
        for previous in interrupted:
            store.put(
                "automation_runs", previous["id"], {**previous, "status": "interrupted"}
            )
            current = config(previous["mailbox"])
            if current.get("version"):
                update(
                    AutomationInput(
                        **{k: current[k] for k in DEFAULT} | {"paused": True}
                    ),
                    previous["mailbox"],
                )
        if interrupted:
            return None
        runtime = store.get("automation_runtime", mailbox) or {}
        at = datetime.now(timezone.utc)
        if (next_at := instant(runtime.get("next_tick_at"))) and next_at > at:
            return None
        store.put(
            "automation_runtime",
            mailbox,
            {
                "next_tick_at": (at + timedelta(minutes=2)).isoformat(),
                "last_started_at": now(),
            },
        )
        run = {
            "id": uuid4().hex,
            "mailbox": mailbox,
            "status": "running",
            "results": [],
            "lead_exceptions": [],
        }
        store.put("automation_runs", run["id"], run)

        async def renew():
            while True:
                await asyncio.sleep(30)
                try:
                    store.renew_lease(LEASE, owner)
                except Exception:
                    lease_lost.set()
                    return

        heartbeat = asyncio.create_task(renew())
        synced = False
        try:
            await process_inbox_batch()
            synced = True
            run["results"].append({"stage": "sync", "status": "completed"})
        except Exception as exc:
            run["results"].append(
                {
                    "stage": "sync",
                    "status": "blocked",
                    "reason": f"Gmail sync unavailable ({type(exc).__name__}); reply/follow-up drafting waits for a successful sync",
                }
            )
        if _active(mailbox, saved, stop) and synced:
            await asyncio.to_thread(_replies, mailbox, saved, run, stop)
        if _active(mailbox, saved, stop) and _window(saved, at):
            if saved["research_enabled"]:
                job_id = research_prefix(mailbox) + str(at.astimezone(TZ).date())
                try:
                    job = store.get(
                        "research_jobs", job_id
                    ) or research_jobs.create_job(
                        saved["location"],
                        saved["industry"],
                        saved["research_results"],
                        saved["research_requests"],
                        job_id=job_id,
                    )
                    run["results"].append(
                        {"stage": "research", "status": job["status"], "job_id": job_id}
                    )
                    # Close the pause-versus-job-creation race.
                    if not _active(mailbox, saved, stop):
                        research_jobs.control_job(job_id, "pause")
                except (ValueError, DiscoveryUnavailable) as exc:
                    run["results"].append(
                        {
                            "stage": "research",
                            "status": "blocked",
                            "reason": str(exc)[:400],
                        }
                    )
            if _active(mailbox, saved, stop) and synced:
                await asyncio.to_thread(_followups, mailbox, saved, run, stop)
            if _active(mailbox, saved, stop):
                await asyncio.to_thread(_initial, mailbox, saved, run, stop)
        if _active(mailbox, saved, stop):
            report = await generate_weekly_report()
            result = {
                "stage": "weekly_report",
                "status": "saved",
                "report_id": report["id"],
            }
            if saved["weekly_report_email"] and _active(mailbox, saved, stop):
                result.update(
                    status="awaiting_approval", approval_id=queue_report(report)["id"]
                )
            run["results"].append(result)
        run["status"] = "completed" if _active(mailbox, saved, stop) else "stopped"
        store.put("automation_runs", run["id"], run)
        return run
    except BaseException:
        if run:
            store.put("automation_runs", run["id"], {**run, "status": "failed"})
            current = config(mailbox)
            update(
                AutomationInput(**{k: current[k] for k in DEFAULT} | {"paused": True}),
                mailbox,
            )
        raise
    finally:
        if heartbeat:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
        store.release_lease(LEASE, owner)


class AutomationRunner:
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
                await tick(self.stopping.is_set)
            except Exception as exc:
                logger.warning("Automation tick failed (%s)", type(exc).__name__)
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self.stopping.wait(), timeout=30)

    async def stop(self):
        if self.task:
            self.stopping.set()
            await self.task
            self.task = None


automation_runner = AutomationRunner()
