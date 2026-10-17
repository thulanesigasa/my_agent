"""Real extraction formatting must not offer logo files as business websites."""

from unittest.mock import AsyncMock

import pytest
from core.store import store
from config import settings
from services.lead_service import (
    ingest_candidate,
    lead_view,
    normalize_inspection,
    observation_fingerprint,
)
from services.source_inspection import inspect_source, parse_evidence
from test_leads_phase4 import candidate

SOURCE = "https://magaweniplumbers.co.za/"
TEXT = """[CALL NOW: +27727605595](tel:+27727605595)
Also call 072 760 5595 or (+27 72 760 5595).
[Logo](https://magaweniplumbers.co.za/wp-content/uploads/logo.png?version=2)
[Contact](/contact)
[Article](http://swapvision.co.za/)
[Plumbing help](https://blog.example.test/help)
"""


def parsed():
    return {
        "source_url": SOURCE,
        "findings": parse_evidence(TEXT, SOURCE, "Standerton"),
    }


def test_phone_variants_deduplicate_and_never_include_closing_parenthesis():
    findings = normalize_inspection(parsed())["findings"]
    assert [item["value"] for item in findings["phones"]] == ["+27727605595"]
    assert findings["links"][0]["value"] == SOURCE + "contact"
    assert len(findings["links"]) == 1
    assert len(findings["external_links"]) == 2
    assert not any(
        "logo.png" in item["value"]
        for kind in ("links", "external_links")
        for item in findings[kind]
    )


@pytest.mark.parametrize(
    "asset",
    [
        "photo.JPG",
        "logo.svg?v=1",
        "file.PDF",
        "bundle.js",
        "font.woff2",
        "logo%2Epng",
        "clip.mp4",
    ],
)
def test_recognized_assets_are_not_website_suggestions(asset):
    result = normalize_inspection(
        {
            "source_url": SOURCE,
            "findings": {"links": [{"value": SOURCE + asset, "evidence": "Asset"}]},
        }
    )
    assert result["findings"]["links"] == result["findings"]["external_links"] == []


def test_legacy_findings_cleaned_in_view_without_reinspection_or_timestamp_change():
    lead = ingest_candidate(candidate(source_url=SOURCE))
    old = {
        "lead_id": lead["id"],
        "source_url": SOURCE,
        "checked_at": "2026-10-17T14:03:30+00:00",
        "expires": 9999999999,
        "fingerprint": observation_fingerprint(lead),
        "findings": {
            "phones": [
                {"value": "+27727605595", "evidence": "call"},
                {"value": "+27727605595)", "evidence": "tel"},
            ],
            "links": [
                {"value": SOURCE + "logo.png", "evidence": "logo"},
                {"value": "http://swapvision.co.za/", "evidence": "article"},
            ],
        },
    }
    store.put("lead_inspections", lead["id"], old)
    viewed = lead_view(lead)["source_inspection"]
    assert viewed["checked_at"] == old["checked_at"]
    assert len(viewed["findings"]["phones"]) == 1
    assert viewed["findings"]["links"] == []
    assert (
        viewed["findings"]["external_links"][0]["value"] == "http://swapvision.co.za/"
    )
    assert store.list("research_limits") == []
    assert store.get("leads", lead["id"]) == lead


@pytest.mark.asyncio
async def test_cached_inspection_is_cleaned_without_provider_call_or_fresh_review_time(
    monkeypatch,
):
    monkeypatch.setattr(settings, "ALLOW_TAVILY_RESEARCH", True)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "fixture-key")
    lead = ingest_candidate(candidate(source_url=SOURCE))
    request = AsyncMock(
        return_value={"results": [{"url": SOURCE, "raw_content": TEXT}]}
    )
    monkeypatch.setattr("services.source_inspection.request_provider", request)
    first = await inspect_source(lead["id"])
    second = await inspect_source(lead["id"])
    assert second["cached"] and request.await_count == 1
    assert first["inspection"] == second["inspection"]
    assert len(second["inspection"]["findings"]["phones"]) == 1
    assert len(second["inspection"]["findings"]["external_links"]) == 2
    assert normalize_inspection(second["inspection"]) == second["inspection"]
