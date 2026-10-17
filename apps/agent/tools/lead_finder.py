"""Core research tools use saved evidence; optional paid search requires explicit opt-in."""

import httpx
from config import settings
from core.store import store
from services.lead_service import ingest_candidate, ensure_qualified, normalized
from services.contacts import EligibilityError


def matching_leads(location, industry):
    return [
        lead
        for lead in store.list("leads")
        if lead.get("status") != "rejected"
        and normalized(location)
        in normalized(lead.get("location") or lead.get("address", ""))
        and (
            industry
            in ("local businesses", "local services", "local service businesses")
            or normalized(industry) in normalized(lead.get("industry", ""))
        )
    ]


async def search_businesses_without_websites(
    location="Standerton, Mpumalanga", industry="local businesses", limit=10
):
    """Return saved candidates, not proof that any business has no website."""
    limit = max(1, min(int(limit), 50))
    saved = matching_leads(location, industry)
    if saved:
        return saved[:limit]
    if not settings.ALLOW_TAVILY_RESEARCH or not settings.TAVILY_API_KEY:
        raise RuntimeError(
            "Lead discovery unavailable for this area: use Leads for free OpenStreetMap discovery or manual/CSV import. Optional Tavily requires explicit ALLOW_TAVILY_RESEARCH=true."
        )
    try:
        async with httpx.AsyncClient(
            timeout=15, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": f"{industry} businesses in {location} contact website",
                    "max_results": min(limit, 10),
                },
            )
            response.raise_for_status()
            data = response.json()
        result = []
        for hit in data.get("results", [])[:limit]:
            if not hit.get("title") or not hit.get("url"):
                continue
            result.append(
                ingest_candidate(
                    {
                        "name": hit["title"],
                        "location": location,
                        "industry": industry,
                        "source": "tavily",
                        "source_url": hit["url"],
                    }
                )
            )
        return result
    except Exception:
        raise RuntimeError("Lead discovery failed; no leads were invented") from None


async def find_contact_email(business_name, location="Standerton, Mpumalanga"):
    """Never guess addresses or promote a search snippet into a verified contact."""
    for lead in store.list("leads"):
        if normalized(lead.get("name", "")) != normalized(business_name) or normalized(
            lead.get("location", "")
        ) != normalized(location):
            continue
        try:
            qualified = ensure_qualified(lead["id"], require_consent=False)
        except EligibilityError:
            continue
        review = qualified["review"]
        return {
            "email": review["email"],
            "confidence": "verified",
            "source": review["contact_source"],
            "requires_review": False,
        }
    return {"email": None, "confidence": "unverified", "source": "not_found"}
