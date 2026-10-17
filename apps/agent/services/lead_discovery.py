"""Bounded, opt-in public OpenStreetMap lookups. No geocoding or paid fallback."""

import asyncio
import hashlib
import json
import math
import time
from uuid import uuid4
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from config import settings
from core.store import store, ConflictError
from services.lead_service import ingest_candidate

ENDPOINT = "https://overpass-api.de/api/interpreter"
ATTRIBUTION = (
    "© OpenStreetMap contributors · ODbL · https://www.openstreetmap.org/copyright"
)
CATEGORIES = {
    "shops": ['["shop"]'],
    "food": ['["amenity"~"^(restaurant|cafe|fast_food|bakery)$"]'],
    "services": ['["craft"]', '["office"]'],
    "all": [
        '["shop"]',
        '["craft"]',
        '["office"]',
        '["amenity"~"^(restaurant|cafe|fast_food)$"]',
    ],
}


class DiscoveryUnavailable(RuntimeError):
    pass


def reserve_request():
    """Durable cooldown/quota shared across API and worker. Failures consume a slot."""
    today = datetime.now(ZoneInfo("Africa/Johannesburg")).date().isoformat()
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT data FROM records WHERE kind='research_limits' AND id='overpass' "
        ).fetchone()
        usage = json.loads(row[0]) if row else {}
        if time.time() - usage.get("last_request", 0) < 120:
            raise ConflictError(
                "Public research cooldown: wait two minutes between new searches"
            )
        count = usage.get("count", 0) if usage.get("day") == today else 0
        if count >= settings.OSM_DAILY_QUERY_LIMIT:
            raise DiscoveryUnavailable(
                "Daily public research limit reached; use manual entry or CSV import"
            )
        db.execute(
            "INSERT INTO records VALUES ('research_limits', 'overpass', ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (
                json.dumps(
                    {"day": today, "count": count + 1, "last_request": time.time()}
                ),
            ),
        )


async def request_overpass(query):
    try:
        async with asyncio.timeout(40), httpx.AsyncClient(
            timeout=httpx.Timeout(35, connect=10),
            trust_env=False,
            follow_redirects=False,
            headers={
                "User-Agent": "my_agent/phase4-small-pilot (OpenStreetMap research)"
            },
        ) as client:
            async with client.stream(
                "POST", ENDPOINT, data={"data": query}
            ) as response:
                response.raise_for_status()
                chunks = []
                length = 0
                async for chunk in response.aiter_bytes():
                    length += len(chunk)
                    if length > 3_000_000:
                        raise DiscoveryUnavailable(
                            "Search response exceeded the size limit; use a smaller radius"
                        )
                    chunks.append(chunk)
        data = json.loads(b"".join(chunks))
        if (
            not isinstance(data, dict)
            or data.get("remark")
            or not isinstance(data.get("elements"), list)
        ):
            raise DiscoveryUnavailable(
                "Public search returned an incomplete response; no partial results were imported"
            )
        return data
    except DiscoveryUnavailable:
        raise
    except Exception:
        raise DiscoveryUnavailable(
            "Public search unavailable or rate limited; try later or import leads manually"
        ) from None


def tagged_url(value):
    value = value.strip()
    if value and "://" not in value:
        value = "https://" + value
    return value


async def discover_osm(
    *, location, latitude, longitude, radius_km=1, category="all", limit=25
):
    if not (
        location.strip()
        and math.isfinite(latitude)
        and -85 <= latitude <= 85
        and math.isfinite(longitude)
        and -180 <= longitude <= 180
        and math.isfinite(radius_km)
        and 0.1 <= radius_km <= 5
        and category in CATEGORIES
        and 1 <= limit <= 50
    ):
        raise ValueError(
            "Enter a location label, valid coordinates, radius 0.1–5 km and limit 1–50"
        )
    fingerprint = f"{location.strip().casefold()}:{latitude:.6f}:{longitude:.6f}:{radius_km:.2f}:{category}:{limit}"
    cache_id = hashlib.sha256(fingerprint.encode()).hexdigest()
    cached = store.get("research_cache", cache_id)
    if cached and cached.get("expires", 0) > time.time():
        return {
            **cached["result"],
            "leads": [
                store.get("leads", i)
                for i in cached["lead_ids"]
                if store.get("leads", i)
            ],
            "cached": True,
        }
    owner = uuid4().hex
    store.acquire_lease("public-lead-research", owner, seconds=120)
    try:
        reserve_request()
        selectors = "".join(
            f'nwr(around:{int(radius_km * 1000)},{latitude:.6f},{longitude:.6f})["name"]{tag};'
            for tag in CATEGORIES[category]
        )
        query = f"[out:json][timeout:25][maxsize:8388608];({selectors});out center {limit + 1};"
        data = await request_overpass(query)
        results = {}
        for element in data["elements"][:limit]:
            tags = element.get("tags", {})
            kind = element.get("type")
            ident = element.get("id")
            if (
                kind not in ("node", "way", "relation")
                or not isinstance(ident, int)
                or not tags.get("name")
            ):
                continue
            source_id = f"{kind}/{ident}"
            address = ", ".join(
                str(tags[k])
                for k in ("addr:housenumber", "addr:street", "addr:suburb", "addr:city")
                if tags.get(k)
            )
            lead = ingest_candidate(
                {
                    "name": tags["name"],
                    "location": location.strip(),
                    "address": address,
                    "phone": tags.get("contact:phone") or tags.get("phone", ""),
                    "email": tags.get("contact:email") or tags.get("email", ""),
                    "website": tagged_url(
                        tags.get("contact:website") or tags.get("website", "")
                    ),
                    "industry": tags.get("shop")
                    or tags.get("craft")
                    or tags.get("office")
                    or tags.get("amenity", ""),
                    "source": "openstreetmap",
                    "source_id": source_id,
                    "source_url": f"https://www.openstreetmap.org/{source_id}",
                }
            )
            results[lead["id"]] = lead
        result = {
            "leads": list(results.values()),
            "cached": False,
            "attribution": ATTRIBUTION,
            "truncated": len(data["elements"]) > limit,
            "query": {
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km,
                "category": category,
                "limit": limit,
            },
            "warning": "Missing website/email tags are not proof of absence. Verify business identity, activity, website and contact sources before outreach.",
        }
        store.put(
            "research_cache",
            cache_id,
            {
                "lead_ids": list(results),
                "expires": time.time() + 86400,
                "result": {k: v for k, v in result.items() if k != "leads"},
            },
        )
        return result
    finally:
        store.release_lease("public-lead-research", owner)
