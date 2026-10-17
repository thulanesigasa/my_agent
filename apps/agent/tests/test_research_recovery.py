"""Provider failure classification, persisted retry timing and shared limits."""

from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from config import Settings, settings
from core.store import store, ConflictError
from services import lead_discovery as discovery


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def fake_provider(monkeypatch, status, headers=None):
    calls = []

    class Stream:
        async def __aenter__(self):
            response = httpx.Response(
                status,
                headers=headers,
                request=httpx.Request("POST", discovery.provider_info()["endpoint"]),
                text="Private upstream diagnostics must not be shown",
            )
            response.raise_for_status()
            return response

        async def __aexit__(self, *args):
            pass

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def stream(self, method, endpoint, **kwargs):
            calls.append(endpoint)
            return Stream()

    monkeypatch.setattr(discovery.httpx, "AsyncClient", lambda **kwargs: Client())
    return calls


def test_default_provider_is_fixed_free_endpoint_and_rejects_arbitrary_urls():
    config = Settings(_env_file=None)
    assert config.OSM_PROVIDER == "private_coffee"
    assert (
        discovery.provider_info()["endpoint"]
        == "https://overpass.private.coffee/api/interpreter"
    )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, OSM_PROVIDER="http://127.0.0.1")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [502, 503, 504])
async def test_gateway_errors_are_specific_and_do_not_rotate_or_retry(
    monkeypatch, status
):
    calls = fake_provider(monkeypatch, status)
    with pytest.raises(discovery.DiscoveryUnavailable) as caught:
        await discovery.request_overpass("fixture")
    assert f"HTTP {status}" in str(caught.value)
    assert "Private upstream" not in str(caught.value)
    assert caught.value.retry_after == 120
    assert discovery.cooldown_remaining() > 0
    assert len(calls) == 1
    assert store.list("leads") == []


def test_api_returns_retry_hint_and_restores_countdown_without_spending_more_requests(
    api, monkeypatch
):
    calls = fake_provider(monkeypatch, 502)
    body = {"location": "Example Town", "latitude": 0, "longitude": 0}
    failed = api.post("/api/leads/discover", json=body)
    assert failed.status_code == 503
    assert "HTTP 502" in failed.json()["detail"]["message"]
    assert failed.json()["detail"]["retry_after_seconds"] == 120
    assert failed.headers["Retry-After"] == "120"
    blocked = api.post("/api/leads/discover", json=body)
    assert blocked.status_code == 409
    assert 0 < blocked.json()["detail"]["retry_after_seconds"] <= 120
    status = api.get("/api/leads").json()
    assert (
        status["provider"]["id"] == "private_coffee"
        and status["retry_after_seconds"] > 0
    )
    assert store.get("research_limits", "overpass")["count"] == 1
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_provider_switch_preserves_upstream_rate_limit_and_shared_budget(
    monkeypatch,
):
    calls = fake_provider(monkeypatch, 429, {"Retry-After": "600"})
    with pytest.raises(discovery.DiscoveryUnavailable) as caught:
        await discovery.discover_osm(location="Example Town", latitude=0, longitude=0)
    assert "rate limiting" in str(caught.value)
    assert caught.value.retry_after == 600
    monkeypatch.setattr(settings, "OSM_PROVIDER", "main")
    with pytest.raises(ConflictError):
        await discovery.discover_osm(location="Example Town", latitude=0, longitude=0)
    assert len(calls) == 1
    assert store.get("research_limits", "overpass")["count"] == 1
    assert discovery.cooldown_remaining() > 590


@pytest.mark.asyncio
async def test_provider_cache_entries_are_separate(monkeypatch):
    fetch = AsyncMock(return_value={"elements": []})
    monkeypatch.setattr(discovery, "request_overpass", fetch)
    args = {"location": "Example Town", "latitude": 0, "longitude": 0}
    first = await discovery.discover_osm(**args)
    assert first["provider"]["id"] == "private_coffee"
    assert (await discovery.discover_osm(**args))["cached"]
    usage = store.get("research_limits", "overpass")
    store.put("research_limits", "overpass", {**usage, "last_request": 0})
    monkeypatch.setattr(settings, "OSM_PROVIDER", "main")
    second = await discovery.discover_osm(**args)
    assert not second["cached"] and second["provider"]["id"] == "main"
    assert fetch.await_count == 2
