"""Offline durable job sequencing, atomic budgets, worker ownership and pause checks."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from config import settings
from core.store import store, StateStore
from services import research_jobs as jobs, web_research as web, source_inspection
from services.lead_discovery import DiscoveryUnavailable
from services.lead_service import review_lead
from test_leads_phase4 import review_payload


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_TAVILY_RESEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "fixture-key")
    monkeypatch.setattr(settings, "RESEARCH_JOBS_ENABLED", True)


@pytest.fixture
def api(monkeypatch):
    from main import app

    # Drive the worker explicitly so API tests have no real background requests.
    monkeypatch.setattr(settings, "RESEARCH_JOBS_ENABLED", False)
    with TestClient(app) as client:
        monkeypatch.setattr(settings, "RESEARCH_JOBS_ENABLED", True)
        yield client


def provider(monkeypatch, count=2):
    search = AsyncMock(
        return_value={
            "results": [
                {
                    "title": f"Source {i}",
                    "url": f"https://directory.example.test/branch-{i}",
                }
                for i in range(count)
            ]
        }
    )

    async def extract(operation, body):
        assert operation == "extract"
        return {
            "results": [
                {
                    "url": body["urls"][0],
                    "raw_content": "Example Town branch. Contact owner@business.example.test. We are open.",
                }
            ]
        }

    extraction = AsyncMock(side_effect=extract)
    monkeypatch.setattr(web, "request_search", search)
    monkeypatch.setattr(source_inspection, "request_provider", extraction)
    return search, extraction


def clear_wait(job_id):
    usage = store.get("research_limits", "tavily")
    if usage:
        store.put(
            "research_limits",
            "tavily",
            {**usage, "last_request": 0, "blocked_until": 0},
        )
    jobs.mutate_job(job_id, lambda job: job.update(next_run_at=0))


@pytest.mark.asyncio
async def test_job_discovers_inspects_assesses_and_never_creates_contacts_or_drafts(
    monkeypatch,
):
    search, extraction = provider(monkeypatch)
    job = jobs.create_job("Example Town", "plumbers", limit=2, max_requests=3)
    assert await jobs.run_once()
    assert store.get("research_jobs", job["id"])["stage"] == "inspect"
    # The service raises the cooldown without advancing past an uninspected source.
    await jobs.run_once()
    waiting = store.get("research_jobs", job["id"])
    assert waiting["status"] == "waiting" and waiting["cursor"] == 0
    assert not await jobs.run_once()
    for _ in range(2):
        clear_wait(job["id"])
        await jobs.run_once()
    done = store.get("research_jobs", job["id"])
    assert done["status"] == "completed" and done["cursor"] == 2
    assert done["requests_used"] == 3 and len(done["results"]) == 2
    assert all(
        result["bucket"] == "potential_client" and not result["ready_to_draft"]
        for result in done["results"]
    )
    assert search.await_count == 1 and extraction.await_count == 2
    assert all(
        lead["status"] == "needs_review" and lead["review"] is None
        for lead in store.list("leads")
    )
    assert (
        store.list("contacts")
        == store.list("approvals")
        == store.list("messages")
        == []
    )


@pytest.mark.asyncio
async def test_job_budget_pauses_before_next_request_and_resume_preserves_progress(
    monkeypatch,
):
    search, extraction = provider(monkeypatch)
    job = jobs.create_job("Example Town", "plumbers", limit=2, max_requests=1)
    await jobs.run_once()
    clear_wait(job["id"])
    await jobs.run_once()
    paused = store.get("research_jobs", job["id"])
    assert paused["status"] == "paused" and paused["requests_used"] == 1
    assert paused["cursor"] == 0 and extraction.await_count == 0
    jobs.control_job(job["id"], "resume", 3)
    for _ in range(2):
        clear_wait(job["id"])
        await jobs.run_once()
    done = store.get("research_jobs", job["id"])
    assert done["status"] == "completed" and done["requests_used"] == 3
    assert search.await_count == 1 and extraction.await_count == 2


@pytest.mark.asyncio
async def test_global_budget_pauses_job_without_charging_its_request(monkeypatch):
    provider(monkeypatch)
    job = jobs.create_job("Example Town", "plumbers")
    web.reserve_request()
    usage = store.get("research_limits", "tavily")
    store.put(
        "research_limits", "tavily", {**usage, "last_request": 0, "monthly_used": 100}
    )
    await jobs.run_once()
    saved = store.get("research_jobs", job["id"])
    assert saved["status"] == "paused" and saved["requests_used"] == 0
    assert web.research_status()["daily_used"] == 1


@pytest.mark.asyncio
async def test_cached_job_steps_are_free_even_with_zero_remaining_local_budget(
    monkeypatch,
):
    search, extraction = provider(monkeypatch, count=1)
    first = jobs.create_job("Example Town", "plumbers", limit=1, max_requests=2)
    await jobs.run_once()
    clear_wait(first["id"])
    await jobs.run_once()
    usage = store.get("research_limits", "tavily")
    store.put("research_limits", "tavily", {**usage, "monthly_used": 100})
    second = jobs.create_job("Example Town", "plumbers", limit=1, max_requests=1)
    await jobs.run_once()
    await jobs.run_once()
    done = store.get("research_jobs", second["id"])
    assert done["status"] == "completed" and done["requests_used"] == 0
    assert search.await_count == extraction.await_count == 1


@pytest.mark.asyncio
async def test_pause_during_inflight_step_saves_result_and_stops_next_request(
    monkeypatch,
):
    search, extraction = provider(monkeypatch)
    job = jobs.create_job("Example Town", "plumbers")

    async def pause_during_search(*args):
        jobs.control_job(job["id"], "pause")
        return search.return_value

    search.side_effect = pause_during_search
    await jobs.run_once()
    saved = store.get("research_jobs", job["id"])
    assert saved["status"] == "paused" and saved["stage"] == "inspect"
    assert saved["requests_used"] == 1 and len(saved["lead_ids"]) == 2
    assert not await jobs.run_once()
    extraction.assert_not_awaited()


@pytest.mark.asyncio
async def test_two_workers_cannot_run_or_recover_the_same_live_step(monkeypatch):
    search, _ = provider(monkeypatch)
    started, release = asyncio.Event(), asyncio.Event()

    async def blocked_search(*args):
        started.set()
        await release.wait()
        return search.return_value

    search.side_effect = blocked_search
    job = jobs.create_job("Example Town", "plumbers")
    first = asyncio.create_task(jobs.run_once())
    await asyncio.wait_for(started.wait(), 3)
    assert not await jobs.run_once()
    assert store.get("research_jobs", job["id"])["status"] == "running"
    release.set()
    await first
    assert search.await_count == 1


@pytest.mark.asyncio
async def test_restart_holds_interrupted_steps_and_resume_uses_persisted_cache(
    monkeypatch,
):
    search, _ = provider(monkeypatch, count=1)
    job = jobs.create_job("Example Town", "plumbers", limit=1)
    await jobs.run_once()
    jobs.mutate_job(
        job["id"],
        lambda value: value.update(
            status="running", stage="discover", inflight={"stage": "discover"}
        ),
    )
    assert StateStore(store.path).get("research_jobs", job["id"])["requests_used"] == 1
    await jobs.run_once()
    interrupted = store.get("research_jobs", job["id"])
    assert interrupted["status"] == "paused" and "stopped" in interrupted["message"]
    assert search.await_count == 1
    jobs.control_job(job["id"], "resume")
    await jobs.run_once()
    assert search.await_count == 1
    assert store.get("research_jobs", job["id"])["requests_used"] == 1


@pytest.mark.asyncio
async def test_cancellation_preserves_inflight_marker_for_restart_review(monkeypatch):
    search, _ = provider(monkeypatch)
    entered = asyncio.Event()

    async def interrupted(*args):
        entered.set()
        await asyncio.Event().wait()

    search.side_effect = interrupted
    job = jobs.create_job("Example Town", "plumbers")
    task = asyncio.create_task(jobs.run_once())
    await asyncio.wait_for(entered.wait(), 3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    saved = store.get("research_jobs", job["id"])
    assert saved["inflight"] and saved["requests_used"] == 1
    assert store.get("leases", "research-job-runner") is None
    await jobs.run_once()
    assert store.get("research_jobs", job["id"])["status"] == "paused"


@pytest.mark.asyncio
async def test_unreadable_source_is_an_exception_and_other_sources_continue(
    monkeypatch,
):
    _, extraction = provider(monkeypatch)
    job = jobs.create_job("Example Town", "plumbers", limit=2)
    await jobs.run_once()
    original = extraction.side_effect

    async def fail_first(operation, body):
        if body["urls"][0].endswith("branch-0"):
            return {
                "results": [],
                "failed_results": [{"error": "private upstream text"}],
            }
        return await original(operation, body)

    extraction.side_effect = fail_first
    for _ in range(2):
        clear_wait(job["id"])
        await jobs.run_once()
    done = store.get("research_jobs", job["id"])
    assert done["status"] == "completed" and done["cursor"] == 2
    assert done["results"][0]["bucket"] == "needs_review"
    assert "private upstream" not in json.dumps(done)


@pytest.mark.asyncio
async def test_provider_error_pauses_without_automatic_retry(monkeypatch):
    search, _ = provider(monkeypatch)
    search.side_effect = DiscoveryUnavailable("Provider temporarily unavailable")
    job = jobs.create_job("Example Town", "plumbers")
    await jobs.run_once()
    assert store.get("research_jobs", job["id"])["status"] == "paused"
    assert not await jobs.run_once() and search.await_count == 1


@pytest.mark.asyncio
async def test_rejected_and_known_website_sources_are_skipped_without_extraction(
    monkeypatch,
):
    _, extraction = provider(monkeypatch)
    job = jobs.create_job("Example Town", "plumbers", limit=2)
    await jobs.run_once()
    ids = store.get("research_jobs", job["id"])["lead_ids"]
    for index, lead_id in enumerate(ids):
        lead = store.get("leads", lead_id)
        review_lead(
            lead_id,
            review_payload(
                lead,
                decision="needs_review" if index else "rejected",
                decision_note="Already unsuitable",
                **(
                    {
                        "website_status": "found",
                        "website_url": "https://business.example.test/",
                    }
                    if index
                    else {}
                ),
            ),
        )
    for _ in range(2):
        await jobs.run_once()
    assert store.get("research_jobs", job["id"])["status"] == "completed"
    extraction.assert_not_awaited()


def test_api_auth_limits_unique_active_job_and_control_conflicts(api, monkeypatch):
    body = {
        "location": "Example Town",
        "industry": "plumbers",
        "limit": 2,
        "max_requests": 3,
    }
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.post("/api/leads/jobs", json=body).status_code == 401
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    assert (
        api.post("/api/leads/jobs", json={**body, "max_requests": 100}).status_code
        == 422
    )
    first = api.post("/api/leads/jobs", json=body)
    assert first.status_code == 202
    job_id = first.json()["id"]
    assert api.post("/api/leads/jobs", json=body).status_code == 409
    assert (
        api.patch(f"/api/leads/jobs/{job_id}", json={"action": "pause"}).status_code
        == 200
    )
    second = api.post("/api/leads/jobs", json=body)
    assert second.status_code == 202
    assert (
        api.patch(f"/api/leads/jobs/{job_id}", json={"action": "resume"}).status_code
        == 409
    )
    assert (
        api.patch("/api/leads/jobs/missing", json={"action": "pause"}).status_code
        == 404
    )
    data = api.get("/api/leads").json()
    assert len(data["research_jobs"]) == 2 and data["research_worker_enabled"]
    assert "fixture-key" not in json.dumps(data)


def test_job_context_reservation_checks_pause_atomically_without_spending():
    job = jobs.create_job("Example Town", "plumbers")
    jobs.mutate_job(
        job["id"], lambda value: value.update(status="running", pause_requested=True)
    )
    token = web.active_research_job.set(job["id"])
    try:
        with pytest.raises(DiscoveryUnavailable, match="paused"):
            web.reserve_request()
    finally:
        web.active_research_job.reset(token)
    assert store.list("research_limits") == []
    assert store.get("research_jobs", job["id"])["requests_used"] == 0


@pytest.mark.asyncio
async def test_background_runner_can_start_and_stop_without_jobs():
    runner = jobs.ResearchJobRunner()
    runner.start()
    task = runner.task
    await asyncio.sleep(0)
    await runner.stop()
    assert task.done() and runner.task is None
    assert store.list("research_limits") == []


@pytest.mark.asyncio
async def test_empty_discovery_completes_without_inspection(monkeypatch):
    search, extraction = provider(monkeypatch, count=0)
    job = jobs.create_job("Example Town", "plumbers")
    await jobs.run_once()
    saved = store.get("research_jobs", job["id"])
    assert saved["status"] == "completed" and saved["results"] == []
    assert saved["requests_used"] == 1 and search.await_count == 1
    extraction.assert_not_awaited()


@pytest.mark.asyncio
async def test_matching_site_email_is_an_uncertain_website_signal_not_qualification(
    monkeypatch,
):
    search, extraction = provider(monkeypatch, count=1)
    search.return_value = {
        "results": [
            {"title": "A plumbing website", "url": "https://business.example.test/"}
        ]
    }
    job = jobs.create_job("Example Town", "plumbers", limit=1)
    await jobs.run_once()
    clear_wait(job["id"])
    await jobs.run_once()
    result = store.get("research_jobs", job["id"])["results"][0]
    assert result["bucket"] == "website_signal" and not result["ready_to_draft"]
    assert store.list("leads")[0]["status"] == "needs_review"
    assert store.list("contacts") == store.list("approvals") == []


def test_active_resumed_job_is_visible_even_with_more_than_twenty_history_entries():
    old = jobs.create_job("Example Town", "plumbers")
    jobs.control_job(old["id"], "pause")
    for index in range(25):
        item = jobs.create_job("Example Town", f"trade-{index}")
        jobs.mutate_job(item["id"], lambda value: value.update(status="completed"))
    jobs.control_job(old["id"], "resume")
    listed = jobs.list_jobs()
    assert len(listed) == 20 and listed[0]["id"] == old["id"]
