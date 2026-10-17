"""Research worker shares the durable evidence ledger with the dashboard/core."""

from tools.lead_finder import search_businesses_without_websites
from services.lead_discovery import discover_osm


async def run_research_agent(
    location="Standerton, Mpumalanga",
    industry="local businesses",
    limit=10,
    latitude=None,
    longitude=None,
    radius_km=1,
    category="all",
):
    if latitude is not None and longitude is not None:
        result = await discover_osm(
            location=location,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            category=category,
            limit=limit,
        )
        leads = result["leads"]
    else:
        leads = await search_businesses_without_websites(location, industry, limit)
    return {
        "agent": "research_agent",
        "status": "completed",
        "location": location,
        "discovered_count": len(leads),
        "leads": leads,
        "next_step": "Review business identity, activity, website and sourced contact evidence in Leads. No email was sent.",
    }
