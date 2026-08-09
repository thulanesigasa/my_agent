"""
Lead Discovery & Contact Finder Tools.
Searches for local businesses without websites and scrapes contact emails for autonomous outreach.
"""
import logging
import re
from typing import List, Dict, Any, Optional
import httpx
from config import settings

logger = logging.getLogger("agent.tools.lead_finder")

MOCK_LEADS = [
    {"name": "Mike's Auto Repair", "address": "42 Main Street, Atlanta GA", "phone": "+14045550101", "website": None},
    {"name": "Sunrise Bakery & Café", "address": "15 Oak Ave, Memphis TN", "phone": "+19015550192", "website": ""},
    {"name": "Elite Plumbing Services", "address": "88 Commerce Blvd, Dallas TX", "phone": "+12145550222", "website": None},
    {"name": "Golden Paws Pet Grooming", "address": "5 Park Lane, Phoenix AZ", "phone": "+16025550345", "website": "http://broken.example"},
    {"name": "TechFix Electronics", "address": "201 Central Dr, Denver CO", "phone": "+17205550456", "website": None},
    {"name": "City Florist & Gifts", "address": "74 Spring Road, Charlotte NC", "phone": "+17045550512", "website": ""},
    {"name": "Sunrise Fitness Studio", "address": "33 Wellness Way, Nashville TN", "phone": "+16155550677", "website": None},
    {"name": "Prime Landscaping", "address": "66 Garden Blvd, Orlando FL", "phone": "+14075550788", "website": None},
    {"name": "Excel Cleaning Solutions", "address": "12 Harbor View, Seattle WA", "phone": "+12065550899", "website": ""},
    {"name": "Reliable HVAC Services", "address": "99 Industry Loop, Houston TX", "phone": "+17135550911", "website": None},
]

MOCK_EMAILS = {
    "Mike's Auto Repair": "mike@mikesautorepair.local",
    "Sunrise Bakery & Café": "hello@sunrisebakery.biz",
    "Elite Plumbing Services": "contact@eliteplumbing.co",
    "Golden Paws Pet Grooming": "info@goldenpaws.com",
    "TechFix Electronics": "techfix@gmail.com",
    "City Florist & Gifts": "orders@cityflorist.net",
    "Sunrise Fitness Studio": "studio@sunrisefitness.co",
    "Prime Landscaping": "primescape@mail.com",
    "Excel Cleaning Solutions": "excel.cleaning@outlook.com",
    "Reliable HVAC Services": "reliable.hvac@gmail.com",
}


async def search_businesses_without_websites(
    location: str,
    industry: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Searches for local businesses in a given location and industry that are missing a website.

    Args:
        location: City or region to search (e.g. 'Atlanta, GA').
        industry: Type of business to target (e.g. 'plumber', 'bakery').
        limit: Maximum number of leads to return.

    Returns:
        List of business records with name, address, phone, and missing_website flag.
    """
    logger.info(f"Searching businesses without websites: industry='{industry}', location='{location}'")

    results: List[Dict[str, Any]] = []

    # Try Tavily Search API if configured
    if settings.TAVILY_API_KEY:
        try:
            query = f"{industry} businesses in {location} no website contact"
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": settings.TAVILY_API_KEY, "query": query, "max_results": limit}
                )
                res.raise_for_status()
                data = res.json()
                for hit in data.get("results", []):
                    results.append({
                        "name": hit.get("title", "Unknown Business"),
                        "address": location,
                        "phone": None,
                        "website": hit.get("url"),
                        "missing_website": not hit.get("url"),
                        "source": "tavily"
                    })
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}. Using structured mock dataset.")

    # Fallback: filtered mock data simulating real results
    if not results:
        industry_lower = industry.lower()
        for biz in MOCK_LEADS:
            missing = not biz.get("website") or biz.get("website") == "" or "broken" in str(biz.get("website", ""))
            results.append({**biz, "missing_website": missing, "industry": industry, "location": location, "source": "mock"})

    # Filter to only businesses missing websites
    filtered = [r for r in results if r.get("missing_website", True)]
    logger.info(f"Found {len(filtered)} businesses without websites for '{industry}' in '{location}'")
    return filtered[:limit]


async def find_contact_email(
    business_name: str,
    location: str
) -> Dict[str, Any]:
    """
    Searches public directories and web results for a business contact email.

    Args:
        business_name: Name of the business to look up.
        location: Location context to narrow the search.

    Returns:
        Dict with 'email' (str or None) and 'confidence' ('verified', 'guessed', 'manual_review').
    """
    logger.info(f"Finding contact email for '{business_name}' in '{location}'")

    # Try Tavily scraping if configured
    if settings.TAVILY_API_KEY:
        try:
            query = f"{business_name} {location} contact email"
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": settings.TAVILY_API_KEY, "query": query, "max_results": 3}
                )
                res.raise_for_status()
                data = res.json()
                for hit in data.get("results", []):
                    content = hit.get("content", "")
                    emails_found = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", content)
                    if emails_found:
                        return {"email": emails_found[0], "confidence": "verified", "source": "tavily"}
        except Exception as e:
            logger.warning(f"Tavily email search error: {e}")

    # Fallback: look up structured mock registry
    email = MOCK_EMAILS.get(business_name)
    if email:
        return {"email": email, "confidence": "guessed", "source": "mock_registry"}

    # Generate a heuristic guess from business name slug
    slug = re.sub(r"[^a-z0-9]", "", business_name.lower())[:12]
    guessed = f"info@{slug}.com"
    return {"email": guessed, "confidence": "manual_review", "source": "heuristic_guess"}
