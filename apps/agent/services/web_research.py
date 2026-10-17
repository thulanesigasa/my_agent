"""Opt-in basic web searches with durable local budgets. No crawling or LLM."""

import asyncio
import hashlib
import json
import math
import time
from contextvars import ContextVar
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from config import settings
from core.store import store
from services.lead_discovery import DiscoveryUnavailable, ResearchCooldown
from services.lead_service import ingest_candidate, normalized, public_url

ENDPOINT = "https://api.tavily.com/search"
active_research_job = ContextVar("active_research_job", default=None)


def research_status():
    stamp = datetime.now(ZoneInfo("Africa/Johannesburg"))
    usage = store.get("research_limits", "tavily") or {}
    return {
        "enabled": settings.ALLOW_TAVILY_RESEARCH,
        "configured": bool(settings.TAVILY_API_KEY and settings.TAVILY_API_KEY.strip()),
        "daily_limit": settings.TAVILY_DAILY_QUERY_LIMIT,
        "monthly_limit": settings.TAVILY_MONTHLY_QUERY_LIMIT,
        "daily_used": (
            usage.get("daily_used", 0)
            if usage.get("day") == stamp.date().isoformat()
            else 0
        ),
        "monthly_used": (
            usage.get("monthly_used", 0)
            if usage.get("month") == stamp.strftime("%Y-%m")
            else 0
        ),
        "retry_after_seconds": max(
            0,
            math.ceil(
                max(usage.get("last_request", 0) + 120, usage.get("blocked_until", 0))
                - time.time()
            ),
        ),
    }


def reserve_request():
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        status = research_status()
        if status["retry_after_seconds"]:
            raise ResearchCooldown(status["retry_after_seconds"])
        if (
            status["daily_used"] >= status["daily_limit"]
            or status["monthly_used"] >= status["monthly_limit"]
        ):
            raise DiscoveryUnavailable(
                "Tavily local daily/monthly research budget reached. No new request was sent."
            )
        job_id = active_research_job.get()
        if job_id:
            row = db.execute(
                "SELECT data FROM records WHERE kind='research_jobs' AND id=?",
                (job_id,),
            ).fetchone()
            job = json.loads(row[0]) if row else None
            if not job or job.get("status") != "running" or job.get("pause_requested"):
                raise DiscoveryUnavailable(
                    "Research job was paused before a new provider request"
                )
            if job["requests_used"] >= job["max_requests"]:
                raise DiscoveryUnavailable(
                    "This research job reached its request budget; increase its budget before resuming"
                )
            job["requests_used"] += 1
            job["updated_at"] = datetime.now(ZoneInfo("UTC")).isoformat()
            db.execute(
                "UPDATE records SET data=? WHERE kind='research_jobs' AND id=?",
                (json.dumps(job), job_id),
            )
        stamp = datetime.now(ZoneInfo("Africa/Johannesburg"))
        usage = {
            "day": stamp.date().isoformat(),
            "month": stamp.strftime("%Y-%m"),
            "daily_used": status["daily_used"] + 1,
            "monthly_used": status["monthly_used"] + 1,
            "last_request": time.time(),
        }
        db.execute(
            "INSERT INTO records VALUES ('research_limits', 'tavily', ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (json.dumps(usage),),
        )


def backoff(seconds=120):
    seconds = max(120, min(86400, seconds))
    usage = store.get("research_limits", "tavily") or {}
    store.put(
        "research_limits",
        "tavily",
        {
            **usage,
            "blocked_until": max(usage.get("blocked_until", 0), time.time() + seconds),
        },
    )
    return seconds


async def request_search(query, limit):
    return await request_provider(
        "search",
        {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": limit,
            "auto_parameters": False,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        },
    )


async def request_provider(operation, payload):
    if operation not in ("search", "extract"):
        raise ValueError("Unsupported research operation")
    try:
        async with asyncio.timeout(40), httpx.AsyncClient(
            timeout=httpx.Timeout(35, connect=10),
            trust_env=False,
            follow_redirects=False,
        ) as client:
            async with client.stream(
                "POST",
                f"https://api.tavily.com/{operation}",
                headers={"Authorization": f"Bearer {settings.TAVILY_API_KEY}"},
                json=payload,
            ) as response:
                response.raise_for_status()
                chunks, length = [], 0
                async for chunk in response.aiter_bytes():
                    length += len(chunk)
                    if length > 2_000_000:
                        raise DiscoveryUnavailable(
                            "Tavily response exceeded the size limit; no results were saved."
                        )
                    chunks.append(chunk)
        data = json.loads(b"".join(chunks))
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("results"), list)
            or data.get("error")
        ):
            raise DiscoveryUnavailable(
                "Tavily returned an invalid response; no results were saved."
            )
        return data
    except DiscoveryUnavailable:
        raise
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        delay = 120
        if status == 429:
            try:
                delay = int(exc.response.headers.get("Retry-After", "120"))
            except ValueError:
                pass
            message = "Tavily rate limit reached (HTTP 429). Wait before another research request."
        elif status in (401, 403):
            message = "Tavily authorization failed. Check the local API key and account access."
        elif status in (432, 433):
            message = "Tavily account usage limit reached. Check the free allowance; no paid fallback was enabled."
        else:
            message = (
                f"Tavily research failed (HTTP {status}). No automatic retry was made."
            )
        raise DiscoveryUnavailable(message, backoff(delay)) from None
    except Exception:
        raise DiscoveryUnavailable(
            "Tavily could not complete the research request. Check connectivity or try later.",
            backoff(),
        ) from None


async def discover_web(*, location, industry, limit=5):
    if (
        not isinstance(limit, int)
        or not 1 <= limit <= 10
        or not location.strip()
        or not industry.strip()
        or len(location) > 200
        or len(industry) > 200
    ):
        raise ValueError(
            "Enter a town and business type (up to 200 characters each), and 1–10 results"
        )
    status = research_status()
    if not status["enabled"] or not status["configured"]:
        raise DiscoveryUnavailable(
            "Tavily research is disabled or not configured. Set the local key and ALLOW_TAVILY_RESEARCH=true, then restart the backend."
        )
    query = f"{industry.strip()} businesses in {location.strip()} public business contact official social profile"
    cache_id = (
        "tavily_"
        + hashlib.sha256(
            f"v1:{normalized(location)}:{normalized(industry)}:{limit}".encode()
        ).hexdigest()
    )
    cached = store.get("research_cache", cache_id)
    if cached and cached.get("expires", 0) > time.time():
        return {
            **cached["result"],
            "leads": [
                lead for i in cached["lead_ids"] if (lead := store.get("leads", i))
            ],
            "cached": True,
            "usage": research_status(),
        }
    owner = uuid4().hex
    store.acquire_lease("tavily-research", owner, seconds=120)
    try:
        reserve_request()
        data = await request_search(query, limit)
        candidates = {}
        skipped = 0
        for hit in data["results"][:limit]:
            if (
                not isinstance(hit, dict)
                or not isinstance(hit.get("title"), str)
                or not hit["title"].strip()
                or not isinstance(hit.get("url"), str)
            ):
                skipped += 1
                continue
            try:
                url = public_url(hit["url"])
            except ValueError:
                skipped += 1
                continue
            # Keep only source references, not snippets, provider answers or guessed emails.
            candidates[url] = {
                "name": hit["title"].strip()[:200],
                "location": location.strip(),
                "industry": industry.strip(),
                "source": "tavily",
                "source_url": url,
                "source_kind": "search_result",
                "source_note": "Unverified web search result. Title may describe a directory or multiple businesses; confirm the exact business and branch against the original source.",
            }
        leads = [ingest_candidate(candidate) for candidate in candidates.values()]
        result = {
            "leads": leads,
            "cached": False,
            "skipped_results": skipped,
            "warning": "Search titles are not verified business names. Results may be directories, unrelated or outdated. Review the original source. Missing website/email details are unknown, not proof of absence.",
        }
        store.put(
            "research_cache",
            cache_id,
            {
                "expires": time.time() + 86400,
                "lead_ids": [lead["id"] for lead in leads],
                "result": {k: v for k, v in result.items() if k != "leads"},
            },
        )
        return {**result, "usage": research_status()}
    finally:
        store.release_lease("tavily-research", owner)
