"""Read one saved public source through Tavily; return evidence, never eligibility."""

import hashlib
import json
import re
import time
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

from core.store import store, now, ConflictError
from services.contacts import normalize_email
from services.lead_service import (
    public_url,
    observation_fingerprint,
    normalize_inspection,
)
from services.lead_discovery import DiscoveryUnavailable
from services.web_research import research_status, reserve_request, request_provider

MAX_TEXT = 200_000
EMAIL = re.compile(
    r"(?<![\w@])[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}(?![\w@])"
)
PHONE = re.compile(r"(?<!\d)(?:\+27[ ().-]*|0)(?:\d[ ().-]*){8}\d(?!\d)")
URL = re.compile(r"https?://[^\s<>\[\]\"']{1,2000}")


class SourceInspectionFailed(DiscoveryUnavailable):
    """A single source was unreadable; a job can record it as an exception."""


def allowed_source(lead):
    url = public_url(lead["source_url"])
    parts = urlsplit(url)
    host = parts.hostname.lower()
    if (
        lead.get("source") == "openstreetmap"
        or host in ("maps.app.goo.gl", "goo.gl", "g.page")
        or (
            re.search(r"(^|\.)google\.[a-z.]+$", host)
            and (parts.path.startswith("/maps") or host.startswith("maps."))
        )
    ):
        raise ValueError(
            "Inspect an original public business source, not a map listing or shortened map link"
        )
    return url


def excerpt(text, start, end):
    return " ".join(text[max(0, start - 55) : min(len(text), end + 55)].split())[:220]


def parse_evidence(text, url, location):
    """Literal pattern matches only; page content cannot issue agent instructions."""
    findings = {
        "emails": [],
        "phones": [],
        "links": [],
        "dates": [],
        "closure_mentions": [],
    }
    seen = {key: set() for key in findings}

    def add(kind, value, start, end):
        if value not in seen[kind] and len(findings[kind]) < 10:
            seen[kind].add(value)
            findings[kind].append(
                {"value": value, "evidence": excerpt(text, start, end)}
            )

    for match in EMAIL.finditer(text):
        try:
            value = normalize_email(match.group())
        except ValueError:
            continue
        add("emails", value, *match.span())
    for match in PHONE.finditer(text):
        add("phones", match.group().strip(" .-"), *match.span())
    for match in URL.finditer(text):
        try:
            value = public_url(match.group().rstrip(").,;"))
        except ValueError:
            continue
        if value != url:
            add("links", value, *match.span())
    for match in re.finditer(r"\[[^\]\n]{1,200}\]\((/[^\s)]{1,1900})\)", text):
        try:
            value = public_url(urljoin(url, match.group(1)))
        except ValueError:
            continue
        if value != url:
            add("links", value, *match.span())
    for match in re.finditer(r"\b20\d{2}-\d{2}-\d{2}\b", text):
        add("dates", match.group(), *match.span())
    for match in re.finditer(
        r"permanently closed|ceased trading|closed down|out of business", text, re.I
    ):
        add("closure_mentions", match.group(), *match.span())
    town = location.split(",")[0].strip()
    return {
        **findings,
        "location_text_seen": bool(
            town and re.search(r"\b" + re.escape(town) + r"\b", text, re.I)
        ),
        "activity_status": "unverified",
        "website_status": "unverified",
        "contact_status": "unverified",
    }


def save_inspection(lead_id, fingerprint, inspection, *, fresh=False):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT data FROM records WHERE kind='leads' AND id=?", (lead_id,)
        ).fetchone()
        if not row or observation_fingerprint(json.loads(row[0])) != fingerprint:
            raise ConflictError(
                "The candidate source changed during inspection; reload and inspect the current source"
            )
        if fresh:
            # Set under the same write lock as publication, so a concurrent review
            # cannot appear to acknowledge findings it could not yet have seen.
            inspection["checked_at"] = now()
        db.execute(
            "INSERT INTO records VALUES ('lead_inspections', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (lead_id, json.dumps(inspection)),
        )


async def inspect_source(lead_id):
    lead = store.get("leads", lead_id)
    if not lead:
        raise KeyError(lead_id)
    url = allowed_source(lead)
    status = research_status()
    if not status["enabled"] or not status["configured"]:
        raise DiscoveryUnavailable(
            "Tavily inspection is disabled or not configured. Enable local Tavily research and restart the backend."
        )
    fingerprint = observation_fingerprint(lead)
    cache_id = (
        "inspect_v1_" + hashlib.sha256(f"{lead_id}:{fingerprint}".encode()).hexdigest()
    )
    cached = store.get("research_cache", cache_id)
    if cached and cached.get("expires", 0) > time.time():
        cleaned = normalize_inspection(cached["inspection"])
        save_inspection(lead_id, fingerprint, cleaned)
        return {
            "inspection": cleaned,
            "cached": True,
            "usage": research_status(),
        }
    owner = uuid4().hex
    store.acquire_lease("tavily-research", owner, seconds=120)
    try:
        reserve_request()
        data = await request_provider(
            "extract",
            {
                "urls": [url],
                "extract_depth": "basic",
                "format": "markdown",
                "include_images": False,
                "include_favicon": False,
                "timeout": 15,
            },
        )
        # One URL only. Failures or changed destinations cannot become absence claims.
        results = data["results"]
        if (
            data.get("failed_results")
            or len(results) != 1
            or not isinstance(results[0], dict)
        ):
            raise SourceInspectionFailed(
                "The source could not be inspected. Activity, email and website status remain unknown.",
                research_status()["retry_after_seconds"],
            )
        result = results[0]
        try:
            returned_url = public_url(result.get("url", ""))
        except (ValueError, AttributeError):
            returned_url = ""
        if returned_url != url:
            raise SourceInspectionFailed(
                "The provider returned a different source URL. Open the source manually; no findings were saved.",
                research_status()["retry_after_seconds"],
            )
        text = result.get("raw_content")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise SourceInspectionFailed(
                "Source content was empty or exceeded the inspection limit. No findings were saved.",
                research_status()["retry_after_seconds"],
            )
        inspection = {
            "lead_id": lead_id,
            "source_url": url,
            "fingerprint": fingerprint,
            "checked_at": now(),
            "expires": time.time() + 86400,
            "findings": parse_evidence(text, url, lead["location"]),
            "warning": "Unverified literal page findings. Directory contacts and linked websites may belong to other businesses. Dates and closure phrases need context. No finding proves current activity, website absence or contact permission.",
        }
        from services.qualification import listing_fields

        try:
            inspection["qualification_fields"] = listing_fields(text)
        except ValueError as exc:
            inspection["qualification_fields"] = {"error": str(exc)}
        inspection = normalize_inspection(inspection)
        save_inspection(lead_id, fingerprint, inspection, fresh=True)
        store.put(
            "research_cache",
            cache_id,
            {"expires": inspection["expires"], "inspection": inspection},
        )
        return {"inspection": inspection, "cached": False, "usage": research_status()}
    finally:
        store.release_lease("tavily-research", owner)
