"""
research_agent Module.
Responsible for finding active small companies on Google that do NOT have websites, specifically targeting Standerton, Mpumalanga.
"""
import logging
from typing import Dict, Any, List
from tools.lead_finder import search_businesses_without_websites, find_contact_email

logger = logging.getLogger("agent.research_agent")


async def run_research_agent(
    location: str = "Standerton, Mpumalanga",
    industry: str = "local service businesses",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Executes research_agent task to find active small businesses in Standerton, Mpumalanga missing official websites.
    """
    logger.info(f"[research_agent] Searching active businesses without websites in '{location}'...")
    
    leads = await search_businesses_without_websites(location=location, industry=industry, limit=limit)
    
    enriched_leads: List[Dict[str, Any]] = []
    for lead in leads:
        contact = await find_contact_email(business_name=lead.get("name", ""), location=location)
        enriched_leads.append({**lead, **contact})
        
    result = {
        "agent": "research_agent",
        "status": "completed",
        "location": location,
        "target": "Small active companies missing websites",
        "discovered_count": len(enriched_leads),
        "leads": enriched_leads,
    }
    
    return result
