"""Offline tests for opt-in search costs, evidence and API/worker boundaries."""

import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from config import settings
from core.store import store, ConflictError
from services import web_research as web
from services.lead_discovery import DiscoveryUnavailable
from services.lead_service import review_lead, lead_view
from test_leads_phase4 import review_payload

ARGS = {"location": "Example Town", "industry": "plumbers", "limit": 5}


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_TAVILY_RESEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "fixture-secret")


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def response(title="Branch plumbing", url="https://business.example.test/branch"):
    return {
        "results": [
            {
                "title": title,
                "url": url,
                "content": "Unverified owner@example.test with no website",
                "raw_content": "Must not be stored",
            }
        ]
    }


def clear_cooldown():
    usage = store.get("research_limits", "tavily")
    store.put(
        "research_limits", "tavily", {**usage, "last_request": 0, "blocked_until": 0}
    )


@pytest.mark.asyncio
async def test_opt_in_and_key_required_before_even_cache_access(monkeypatch):
    request = AsyncMock(return_value=response())
    monkeypatch.setattr(web, "request_search", request)
    monkeypatch.setattr(settings, "ALLOW_TAVILY_RESEARCH", False)
    with pytest.raises(DiscoveryUnavailable, match="disabled"):
        await web.discover_web(**ARGS)
    monkeypatch.setattr(settings, "ALLOW_TAVILY_RESEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "")
    with pytest.raises(DiscoveryUnavailable):
        await web.discover_web(**ARGS)
    request.assert_not_awaited()
    assert store.list("research_limits") == []


@pytest.mark.asyncio
async def test_search_sources_not_emails_activity_or_website_findings_and_cache_is_free(
    monkeypatch,
):
    request = AsyncMock(return_value=response())
    monkeypatch.setattr(web, "request_search", request)
    first = await web.discover_web(**ARGS)
    second = await web.discover_web(**ARGS)
    assert second["cached"] and request.await_count == 1
    lead = first["leads"][0]
    assert lead["observation"]["email"] == lead["observation"]["website"] == ""
    assert lead["observation"]["source_kind"] == "search_result"
    assert "content" not in lead["observation"]
    assert not lead_view(lead)["ready_to_draft"] and lead["missing_website"] is None
    assert store.list("contacts") == store.list("approvals") == []
    assert (
        web.research_status()["daily_used"]
        == web.research_status()["monthly_used"]
        == 1
    )


@pytest.mark.asyncio
async def test_same_url_deduplicates_across_queries_and_title_changes_preserving_rejection(
    monkeypatch,
):
    request = AsyncMock(return_value=response())
    monkeypatch.setattr(web, "request_search", request)
    first = (await web.discover_web(**ARGS))["leads"][0]
    review_lead(
        first["id"],
        review_payload(
            first, decision="rejected", decision_note="Directory rather than a business"
        ),
    )
    clear_cooldown()
    request.return_value = response(title="A changed search title")
    again = (await web.discover_web(**{**ARGS, "industry": "plumbing"}))["leads"][0]
    assert again["id"] == first["id"] and again["status"] == "rejected"
    assert len(store.list("leads")) == 1


@pytest.mark.asyncio
async def test_exact_name_required_for_search_result_qualification_and_preserved_on_reimport(
    monkeypatch,
):
    monkeypatch.setattr(web, "request_search", AsyncMock(return_value=response()))
    lead = (await web.discover_web(**ARGS))["leads"][0]
    with pytest.raises(ValueError, match="exact business"):
        review_lead(lead["id"], review_payload(lead))
    reviewed = review_lead(
        lead["id"], review_payload(lead, confirmed_name="Actual branch name")
    )
    assert reviewed["name"] == "Actual branch name"
    clear_cooldown()
    again = (await web.discover_web(**{**ARGS, "limit": 4}))["leads"][0]
    assert again["name"] == "Actual branch name"


@pytest.mark.asyncio
async def test_invalid_urls_and_shapes_skipped_without_partial_unvalidated_writes(
    monkeypatch,
):
    monkeypatch.setattr(
        web,
        "request_search",
        AsyncMock(
            return_value={
                "results": [
                    None,
                    {"title": "Bad", "url": "http://127.0.0.1/x"},
                    {"title": "Bad", "url": "javascript:alert(1)"},
                    {"title": "", "url": "https://example.test"},
                    response()["results"][0],
                ]
            }
        ),
    )
    result = await web.discover_web(**ARGS)
    assert result["skipped_results"] == 4 and len(result["leads"]) == 1


@pytest.mark.asyncio
async def test_failure_consumes_budget_and_releases_lease(monkeypatch):
    request = AsyncMock(side_effect=DiscoveryUnavailable("Unavailable"))
    monkeypatch.setattr(web, "request_search", request)
    with pytest.raises(DiscoveryUnavailable):
        await web.discover_web(**ARGS)
    assert web.research_status()["daily_used"] == 1
    assert store.get("leases", "tavily-research") is None
    assert store.list("leads") == []
    with pytest.raises(ConflictError):
        await web.discover_web(**ARGS)
    assert request.await_count == 1


@pytest.mark.asyncio
async def test_empty_cache_remains_free_after_budget_is_exhausted(monkeypatch):
    request = AsyncMock(return_value={"results": []})
    monkeypatch.setattr(web, "request_search", request)
    first = await web.discover_web(**ARGS)
    assert first["leads"] == []
    usage = store.get("research_limits", "tavily")
    store.put(
        "research_limits", "tavily", {**usage, "last_request": 0, "monthly_used": 100}
    )
    cached = await web.discover_web(**ARGS)
    assert cached["cached"] and cached["leads"] == []
    with pytest.raises(DiscoveryUnavailable, match="budget"):
        await web.discover_web(**{**ARGS, "location": "Another Town"})
    assert request.await_count == 1


@pytest.mark.asyncio
async def test_active_shared_lease_blocks_search_without_spending_a_slot(monkeypatch):
    request = AsyncMock(return_value=response())
    monkeypatch.setattr(web, "request_search", request)
    store.acquire_lease("tavily-research", "another-worker", seconds=120)
    with pytest.raises(ConflictError):
        await web.discover_web(**ARGS)
    request.assert_not_awaited()
    assert store.list("research_limits") == []


def test_daily_and_monthly_budgets_are_atomic_and_survive_new_connections():
    def reserve(_):
        try:
            web.reserve_request()
            return True
        except ConflictError:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(reserve, range(4))) == 1
    clear_cooldown()
    usage = store.get("research_limits", "tavily")
    store.put("research_limits", "tavily", {**usage, "daily_used": 5})
    with pytest.raises(DiscoveryUnavailable, match="budget"):
        web.reserve_request()
    store.put(
        "research_limits", "tavily", {**usage, "daily_used": 0, "monthly_used": 100}
    )
    with pytest.raises(DiscoveryUnavailable, match="budget"):
        web.reserve_request()
    store.put(
        "research_limits",
        "tavily",
        {
            **usage,
            "day": "2000-01-01",
            "month": "2000-01",
            "daily_used": 5,
            "monthly_used": 100,
        },
    )
    web.reserve_request()
    assert (
        web.research_status()["daily_used"]
        == web.research_status()["monthly_used"]
        == 1
    )


@pytest.mark.asyncio
async def test_core_and_dashboard_share_same_budget(monkeypatch, api):
    from tools.lead_finder import search_businesses_without_websites

    request = AsyncMock(return_value=response())
    monkeypatch.setattr(web, "request_search", request)
    first = api.post("/api/leads/research", json=ARGS)
    assert first.status_code == 200
    with pytest.raises(ConflictError):
        await search_businesses_without_websites("Different Town", "plumbers")
    assert request.await_count == 1
    status = api.get("/api/leads").json()["web_research"]
    assert status["daily_used"] == 1 and status["retry_after_seconds"] > 0
    assert "fixture-secret" not in json.dumps(status)


def test_research_api_auth_validation_and_disabled_status(api, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.post("/api/leads/research", json=ARGS).status_code == 401
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    assert (
        api.post("/api/leads/research", json={**ARGS, "limit": 50}).status_code == 422
    )
    assert (
        api.post("/api/leads/research", json={**ARGS, "industry": " "}).status_code
        == 400
    )
    monkeypatch.setattr(settings, "ALLOW_TAVILY_RESEARCH", False)
    assert api.post("/api/leads/research", json=ARGS).status_code == 503
    assert store.list("research_limits") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 401, 429, 432, 433, 500])
async def test_provider_payload_is_basic_bounded_and_errors_do_not_leak_secrets(
    monkeypatch, status
):
    original = httpx.AsyncClient
    calls = []

    def handle(request):
        calls.append(request)
        assert str(request.url) == web.ENDPOINT
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer fixture-secret"
        assert body["search_depth"] == "basic" and body["auto_parameters"] is False
        assert body["include_raw_content"] is False and body["include_answer"] is False
        assert "api_key" not in body and body["max_results"] == 5
        return httpx.Response(
            status,
            json=response() if status == 200 else {"error": "fixture-secret"},
            headers={"Retry-After": "600"},
        )

    monkeypatch.setattr(
        web.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    if status == 200:
        assert len((await web.discover_web(**ARGS))["leads"]) == 1
    else:
        with pytest.raises(DiscoveryUnavailable) as caught:
            await web.discover_web(**ARGS)
        assert "fixture-secret" not in str(caught.value)
        assert caught.value.retry_after == (600 if status == 429 else 120)
        assert store.list("leads") == []
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [b"not json", b'{"results":{}}', b"x" * 2_000_001],
    ids=["invalid-json", "invalid-results", "oversized"],
)
async def test_invalid_or_oversized_responses_save_no_leads(monkeypatch, content):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        web.httpx,
        "AsyncClient",
        lambda **kwargs: original(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=content)
            ),
            **kwargs,
        ),
    )
    with pytest.raises(DiscoveryUnavailable):
        await web.discover_web(**ARGS)
    assert store.list("leads") == []
