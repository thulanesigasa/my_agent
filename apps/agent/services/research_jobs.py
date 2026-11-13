"""Durable, explicitly started research jobs. Never compose or dispatch outreach."""

import asyncio
import json
import logging
import time
from contextlib import suppress
from urllib.parse import urlsplit
from uuid import uuid4

from config import settings
from core.store import store, now, ConflictError
from services.lead_discovery import DiscoveryUnavailable, ResearchCooldown
from services.lead_service import lead_view, TARGET_STATES
from services.source_inspection import inspect_source, SourceInspectionFailed
from services.web_research import discover_web, active_research_job, research_status

ACTIVE = ("queued", "running", "waiting")
logger = logging.getLogger(__name__)


def list_jobs():
    return sorted(
        store.list("research_jobs"),
        key=lambda job: (job.get("status") in ACTIVE, job.get("updated_at", "")),
        reverse=True,
    )[:20]


def mutate_job(job_id, update):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT data FROM records WHERE kind='research_jobs' AND id=?", (job_id,)
        ).fetchone()
        if not row:
            raise KeyError(job_id)
        job = json.loads(row[0])
        update(job)
        job["updated_at"] = now()
        db.execute(
            "UPDATE records SET data=? WHERE kind='research_jobs' AND id=?",
            (json.dumps(job), job_id),
        )
    return job


def create_job(
    location, industry, limit=2, max_requests=3, *, job_id=None, auto_qualify=False
):
    if (
        not location.strip()
        or not industry.strip()
        or len(location) > 200
        or len(industry) > 200
        or not 1 <= limit <= 10
        or not 1 <= max_requests <= 10
    ):
        raise ValueError(
            "Provide a town, business type, 1–10 results and a total job budget of 1–10 requests"
        )
    status = research_status()
    if (
        not settings.RESEARCH_JOBS_ENABLED
        or not status["enabled"]
        or not status["configured"]
    ):
        raise DiscoveryUnavailable(
            "Enable the research worker and configure Tavily before starting a job"
        )
    job = {
        "id": uuid4().hex,
        "location": location.strip(),
        "industry": industry.strip(),
        "limit": limit,
        "max_requests": max_requests,
        "requests_used": 0,
        "status": "queued",
        "stage": "discover",
        "lead_ids": [],
        "cursor": 0,
        "results": [],
        "pause_requested": False,
        "next_run_at": 0,
        "message": "Queued for automatic discovery",
        "created_at": now(),
        "updated_at": now(),
        "inflight": None,
        "auto_qualify": auto_qualify,
    }
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if job_id:
            row = db.execute(
                "SELECT data FROM records WHERE kind='research_jobs' AND id=?",
                (job_id,),
            ).fetchone()
            if row:
                existing = json.loads(row[0])
                if (
                    existing["location"],
                    existing["industry"],
                    existing["limit"],
                    existing["max_requests"],
                ) != (location.strip(), industry.strip(), limit, max_requests):
                    raise ConflictError("Saved research job has different settings")
                return existing
            job["id"] = job_id
        rows = db.execute(
            "SELECT data FROM records WHERE kind='research_jobs'"
        ).fetchall()
        if any(json.loads(row[0]).get("status") in ACTIVE for row in rows):
            raise ConflictError(
                "Another research job is active; pause it before starting another"
            )
        db.execute(
            "INSERT INTO records VALUES ('research_jobs', ?, ?)",
            (job["id"], json.dumps(job)),
        )
    return job


def control_job(job_id, action, max_requests=None):
    def update(job):
        if action == "pause":
            if job["status"] == "completed":
                return
            if job["status"] == "running":
                job.update(
                    pause_requested=True,
                    message="Pause requested; finishing the current step",
                )
            else:
                job.update(
                    status="paused",
                    pause_requested=False,
                    message="Paused by operator",
                    next_run_at=0,
                )
        elif action == "resume":
            if job["status"] != "paused":
                raise ConflictError("Only a paused job can resume")
            budget = max_requests if max_requests is not None else job["max_requests"]
            if not 1 <= budget <= 10 or budget < job["requests_used"]:
                raise ValueError(
                    "The total job budget must be 1–10 and cannot be below requests already used"
                )
            # The write lock serializes resume against creation and other controls.
            if any(
                other["id"] != job_id and other.get("status") in ACTIVE
                for other in store.list("research_jobs")
            ):
                raise ConflictError(
                    "Pause the other active job before resuming this one"
                )
            job.update(
                status="queued",
                pause_requested=False,
                max_requests=budget,
                next_run_at=0,
                inflight=None,
                message="Resumed from the saved step",
            )
        else:
            raise ValueError("Choose pause or resume")

    return mutate_job(job_id, update)


def assess(lead):
    """Triage is a research snapshot, never a modification of human evidence."""
    view = lead_view(lead)
    review = lead.get("review") or {}
    inspection = view.get("source_inspection") or {}
    findings = inspection.get("findings") or {}
    flags = []
    if lead.get("status") == "rejected" or review.get("business_status") == "inactive":
        bucket, reason = (
            "excluded",
            "Operator rejected this candidate or recorded it closed",
        )
    elif review.get("website_status") == "found":
        bucket, reason = "website_found", "Operator recorded an independent website"
    elif review.get("website_status") in TARGET_STATES:
        bucket, reason = (
            "potential_client",
            "Operator recorded a no-independent-website finding; full eligibility still applies",
        )
    else:
        bucket, reason = (
            "needs_review",
            "Website ownership/absence and current business activity need review",
        )
    if not inspection or inspection.get("stale"):
        flags.append("No current source inspection")
    if not findings.get("emails"):
        flags.append("No email identified in inspected text")
    elif len(findings["emails"]) > 1:
        flags.append("Multiple email candidates; check which belongs to the branch")
    if not findings.get("location_text_seen"):
        flags.append("Target town not confirmed by inspected text")
    if findings.get("closure_mentions"):
        flags.append("Closure wording needs context")
    host = (urlsplit(lead["source_url"]).hostname or "").removeprefix("www.")
    if any(
        item["value"].rsplit("@", 1)[-1] == host for item in findings.get("emails", [])
    ):
        if bucket == "needs_review":
            bucket, reason = (
                "website_signal",
                "Published email domain matches the inspected site; check whether this is an existing business website",
            )
        flags.append(
            "Email domain matches the source site; this may already be the business website"
        )
    if (
        bucket == "needs_review"
        and findings.get("emails")
        and findings.get("location_text_seen")
        and not findings.get("closure_mentions")
    ):
        bucket, reason = (
            "potential_client",
            "Published email and town text found; business identity, activity and website absence remain unverified",
        )
    return {
        "lead_id": lead["id"],
        "name": lead["name"],
        "bucket": bucket,
        "reason": reason,
        "flags": flags,
        "email_candidates": len(findings.get("emails", [])),
        "assessed_at": now(),
        "ready_to_draft": view["ready_to_draft"],
    }


def finish(job_id, **changes):
    def update(job):
        job.update(changes, inflight=None)
        if job.get("pause_requested") and job["status"] != "completed":
            job.update(
                status="paused",
                pause_requested=False,
                next_run_at=0,
                message="Paused after the current step",
            )

    return mutate_job(job_id, update)


async def advance(job):
    """Exactly one saved step under the runner lease; caches consume no budget."""
    if job["stage"] == "discover":
        result = await discover_web(
            location=job["location"], industry=job["industry"], limit=job["limit"]
        )
        ids = list(dict.fromkeys(lead["id"] for lead in result["leads"]))
        finish(
            job["id"],
            lead_ids=ids,
            stage="inspect",
            status="queued" if ids else "completed",
            message=(
                f"Discovered {len(ids)} source candidates; beginning inspection"
                if ids
                else "Completed: no source candidates returned"
            ),
        )
        return
    if job["cursor"] >= len(job["lead_ids"]):
        finish(
            job["id"],
            status="completed",
            message="Research completed. Review the shortlist and exceptions in Leads.",
        )
        return
    lead_id = job["lead_ids"][job["cursor"]]
    lead = store.get("leads", lead_id)
    if not lead:
        raise ValueError("Saved candidate is missing; review this job")
    if job["stage"].startswith("qualify_"):
        from services import qualification

        outcome = await qualification.advance(lead, job["stage"])
        if outcome.get("next_stage"):
            finish(
                job["id"],
                stage=outcome["next_stage"],
                status="queued",
                message="Automatic qualification: checking corroborating evidence",
            )
            return
        _complete_candidate(job, store.get("leads", lead_id), qualification=outcome)
        return
    review = lead.get("review") or {}
    # Known unsuitable candidates do not consume extraction requests.
    exception = None
    if (
        lead.get("status") != "rejected"
        and review.get("business_status") != "inactive"
        and review.get("website_status") != "found"
    ):
        try:
            await inspect_source(lead_id)
        except ConflictError:
            raise
        except (SourceInspectionFailed, ValueError) as exc:
            exception = str(exc)
        lead = store.get("leads", lead_id)
    if job.get("auto_qualify") and not exception:
        from services import qualification

        current = store.get("research_jobs", job["id"])
        outcome = qualification.start(
            lead, current["max_requests"] - current["requests_used"]
        )
        if outcome.get("next_stage"):
            finish(
                job["id"],
                stage=outcome["next_stage"],
                status="queued",
                message="Automatic qualification: searching for website and a corroborating source",
            )
            return
        _complete_candidate(job, lead, qualification=outcome)
        return
    _complete_candidate(job, lead, exception=exception)


def _complete_candidate(job, lead, *, exception=None, qualification=None):
    result = assess(lead)
    if qualification:
        result["qualification"] = qualification
        result["reason"] = qualification["reason"]
        result["bucket"] = (
            "automatically_qualified"
            if qualification["decision"] == "qualified"
            else qualification["decision"]
        )
    if exception:
        result.update(
            bucket="needs_review", reason="Source inspection needs manual review"
        )
        result["flags"].append(exception)
    cursor = job["cursor"] + 1
    finish(
        job["id"],
        cursor=cursor,
        stage="inspect",
        results=job["results"] + [result],
        status="completed" if cursor == len(job["lead_ids"]) else "queued",
        message=f"Assessed {cursor} / {len(job['lead_ids'])} sources; findings require review",
    )


async def run_once():
    if not settings.RESEARCH_JOBS_ENABLED:
        return False
    jobs = store.list("research_jobs")
    if not any(job.get("status") in ACTIVE for job in jobs):
        return False
    owner = uuid4().hex
    try:
        store.acquire_lease("research-job-runner", owner, seconds=120)
    except ConflictError:
        return False
    try:
        # Owning this lease means no other live worker can be processing a step.
        for job in store.list("research_jobs"):
            if job["status"] == "running":
                finish(
                    job["id"],
                    status="paused",
                    message="Backend stopped during a step. Review and resume; a completed provider request may have consumed an attempt.",
                )
        job = next(
            (
                job
                for job in store.list("research_jobs")
                if job["status"] in ("queued", "waiting")
                and job.get("next_run_at", 0) <= time.time()
            ),
            None,
        )
        if not job:
            return False

        def claim(current):
            if current["status"] not in ("queued", "waiting"):
                raise ConflictError("Job changed before processing")
            current.update(
                status="running",
                inflight={
                    "stage": current["stage"],
                    "cursor": current["cursor"],
                    "started_at": now(),
                },
                message="Processing saved research step",
            )

        try:
            job = mutate_job(job["id"], claim)
        except ConflictError:
            return False
        token = active_research_job.set(job["id"])
        try:
            await advance(job)
        except ResearchCooldown as exc:
            finish(
                job["id"],
                status="waiting",
                next_run_at=time.time() + exc.retry_after,
                message=f"Waiting {exc.retry_after} seconds for the shared research cooldown",
            )
        except (DiscoveryUnavailable, ConflictError, ValueError, KeyError) as exc:
            finish(
                job["id"],
                status="paused",
                message=(
                    str(exc)
                    if not isinstance(exc, KeyError)
                    else "A saved candidate is missing; review before resuming"
                ),
            )
        except Exception as exc:
            logger.error("Research job step failed (%s)", type(exc).__name__)
            finish(
                job["id"],
                status="paused",
                message="Research step failed. Review configuration and saved progress before resuming.",
            )
        finally:
            active_research_job.reset(token)
        return True
    finally:
        store.release_lease("research-job-runner", owner)


class ResearchJobRunner:
    def __init__(self):
        self.task = None

    def start(self):
        if not self.task or self.task.done():
            self.task = asyncio.create_task(self.loop())

    async def loop(self):
        while True:
            try:
                await run_once()
            except Exception as exc:
                logger.error("Research runner paused a tick (%s)", type(exc).__name__)
            await asyncio.sleep(2)

    async def stop(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None


research_job_runner = ResearchJobRunner()
