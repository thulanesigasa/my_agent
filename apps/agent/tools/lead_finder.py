"""
Lead Discovery & Contact Finder Tools.
Searches for local businesses without websites in Standerton, Mpumalanga and scrapes contact emails for autonomous outreach.
"""

import logging
import hashlib
from core.store import store
import re
from typing import List, Dict, Any
import httpx
from config import settings

logger = logging.getLogger("agent.tools.lead_finder")


async def search_businesses_without_websites(
    location: str = "Standerton, Mpumalanga",
    industry: str = "local businesses",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Returns unqualified search candidates for later website and identity review.

    Args:
        location: City or region to search (default: 'Standerton, Mpumalanga').
        industry: Type of business to target (e.g. 'plumber', 'auto repair', 'bakery').
        limit: Maximum number of leads to return.

    Returns:
        List of business records with name, address, phone, and missing_website flag.
    """
    if not location or location.strip() == "":
        location = "Standerton, Mpumalanga"

    logger.info(
        f"Searching businesses without websites: industry='{industry}', location='{location}'"
    )

    if not settings.TAVILY_API_KEY:
        raise RuntimeError(
            "Lead discovery unavailable: configure Tavily or supply reviewed leads"
        )

    results: List[Dict[str, Any]] = []

    # Try Tavily Search API if configured
    if settings.TAVILY_API_KEY:
        try:
            query = f"{industry} active businesses in {location} no website contact"
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "max_results": limit,
                    },
                )
                res.raise_for_status()
                data = res.json()
                for hit in data.get("results", []):
                    results.append(
                        {
                            "name": hit.get("title", "Unknown Business"),
                            "address": location,
                            "phone": None,
                            "website": None,
                            "missing_website": None,
                            "source_url": hit.get("url"),
                            "requires_review": True,
                            "website_check": "not_checked",
                            "source": "tavily",
                        }
                    )
        except Exception as e:
            raise RuntimeError("Lead discovery failed; no leads were invented") from e

    # Search results are candidates, not proof that a business has no website.
    persisted = []
    for candidate in results[:limit]:
        record_id = hashlib.sha256(
            f"{candidate['name'].strip().lower()}|{location.strip().lower()}".encode()
        ).hexdigest()[:24]
        previous = store.get("leads", record_id) or {}
        persisted.append(
            store.put(
                "leads", record_id, {**previous, **candidate, "location": location}
            )
        )
    return persisted


async def find_contact_email(
    business_name: str, location: str = "Standerton, Mpumalanga"
) -> Dict[str, Any]:
    """
    Searches public directories and web results for a business contact email in Standerton, Mpumalanga.

    Args:
        business_name: Name of the business to look up.
        location: Location context (default: 'Standerton, Mpumalanga').

    Returns:
        Dict with 'email' (str or None) and 'confidence'.
    """
    logger.info(f"Finding contact email for '{business_name}' in '{location}'")

    if settings.TAVILY_API_KEY:
        try:
            query = f"{business_name} {location} contact email"
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "max_results": 3,
                    },
                )
                res.raise_for_status()
                data = res.json()
                for hit in data.get("results", []):
                    content = hit.get("content", "")
                    emails_found = re.findall(
                        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", content
                    )
                    if emails_found:
                        return {
                            "email": emails_found[0],
                            "confidence": "unverified",
                            "source": hit.get("url"),
                            "requires_review": True,
                        }
        except Exception as e:
            logger.warning(f"Tavily email search error: {e}")

    return {"email": None, "confidence": "unverified", "source": "not_found"}
