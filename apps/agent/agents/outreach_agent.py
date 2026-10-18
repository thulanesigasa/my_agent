"""
Autonomous Outreach Sub-Graph.
Multi-node LangGraph sub-workflow for: lead discovery -> contact enrichment -> pitch composition -> approval queue.
Enforces T.s Industries unbreakable business rules on all generated pitches.
"""

import logging
from typing import List, Dict, Any, TypedDict

try:
    from langgraph.graph import StateGraph, END  # type: ignore
except ImportError as e:
    logging.warning(f"LangGraph import warning in outreach_agent: {e}.")
    StateGraph = object
    END = "__end__"

from tools.lead_finder import search_businesses_without_websites, find_contact_email
from services.lead_service import ensure_qualified, draft_lead
from services.contacts import EligibilityError
from services.email_service import email_service
from services.proposals import create_preview

logger = logging.getLogger("agent.outreach")


class OutreachState(TypedDict, total=False):
    """State schema for the outreach sub-graph pipeline."""

    location: str
    industry: str
    leads: List[Dict[str, Any]]
    enriched_leads: List[Dict[str, Any]]
    drafted_pitches: List[Dict[str, Any]]
    sender: str
    outreach_status: str


async def find_leads_node(state: OutreachState) -> OutreachState:
    """
    Node 1: Searches for businesses without websites and populates state['leads'].
    """
    location = state.get("location", "Standerton, Mpumalanga")
    industry = state.get("industry", "local services")
    logger.info(
        f"[OutreachGraph] find_leads_node: location='{location}', industry='{industry}'"
    )

    leads = await search_businesses_without_websites(
        location=location, industry=industry, limit=10
    )
    logger.info(
        f"[OutreachGraph] Found {len(leads)} candidates requiring evidence review."
    )

    return {**state, "leads": leads, "sender": "find_leads_node"}


async def enrich_leads_node(state: OutreachState) -> OutreachState:
    """
    Node 2: Enriches each lead with a contact email address.
    """
    leads = state.get("leads", [])
    location = state.get("location", "")
    logger.info(f"[OutreachGraph] enrich_leads_node: enriching {len(leads)} leads...")

    enriched: List[Dict[str, Any]] = []
    for lead in leads:
        contact_info = await find_contact_email(
            business_name=lead.get("name", ""),
            location=location or lead.get("address", ""),
        )
        enriched.append({**lead, **contact_info})

    logger.info(
        f"[OutreachGraph] Enrichment complete. {len(enriched)} leads with contact data."
    )
    return {**state, "enriched_leads": enriched, "sender": "enrich_leads_node"}


async def compose_pitch_node(state: OutreachState) -> OutreachState:
    """Compose local portfolio proposals only for currently eligible contacts."""
    drafted = []
    for candidate in state.get("enriched_leads", []):
        try:
            preview = create_preview(candidate.get("id"), email_service.expected_email)
        except (EligibilityError, KeyError):
            continue
        drafted.append(
            {
                "recipient_email": preview["recipient_email"],
                "subject": preview["subject"],
                "body": preview["body"],
                "lead_data": {"id": preview["lead_id"]},
                "proposal_preview_id": preview["id"],
            }
        )
    return {**state, "drafted_pitches": drafted, "sender": "compose_pitch_node"}


async def outreach_dispatcher_node(state: OutreachState) -> OutreachState:
    """
    Node 4: Places drafted pitch emails into the human approval queue for review before sending.
    """
    pitches = state.get("drafted_pitches", [])
    logger.info(
        f"[OutreachGraph] outreach_dispatcher_node: queuing {len(pitches)} pitches for approval..."
    )

    queued = 0
    for pitch in pitches:
        lead_id = pitch.get("lead_data", {}).get("id")
        ensure_qualified(lead_id, pitch["recipient_email"])
        draft_lead(
            lead_id,
            pitch["subject"],
            pitch["body"],
            email_service.expected_email,
            pitch.get("proposal_preview_id"),
        )
        queued += 1

    summary = (
        f"{queued} eligible outreach draft(s) available in the Approval Queue.\n"
        f"Review candidates and evidence in Leads. Outreach requires current qualification and recorded permission; sending remains explicitly approved."
    )
    return {**state, "outreach_status": summary, "sender": "outreach_dispatcher_node"}


def build_outreach_subgraph():
    """
    Constructs and returns the compiled outreach sub-graph.
    Returns None gracefully if LangGraph is unavailable.
    """
    if StateGraph is object:
        logger.warning("LangGraph unavailable for outreach sub-graph.")
        return None

    try:
        builder = StateGraph(OutreachState)
        builder.add_node("find_leads", find_leads_node)
        builder.add_node("enrich_leads", enrich_leads_node)
        builder.add_node("compose_pitch", compose_pitch_node)
        builder.add_node("outreach_dispatcher", outreach_dispatcher_node)

        builder.set_entry_point("find_leads")
        builder.add_edge("find_leads", "enrich_leads")
        builder.add_edge("enrich_leads", "compose_pitch")
        builder.add_edge("compose_pitch", "outreach_dispatcher")
        builder.add_edge("outreach_dispatcher", END)

        return builder.compile()
    except Exception as e:
        logger.warning(f"Error compiling outreach sub-graph: {e}")
        return None


outreach_workflow = build_outreach_subgraph()
