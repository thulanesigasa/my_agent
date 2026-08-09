"""
Autonomous Outreach Sub-Graph.
Multi-node LangGraph sub-workflow for: lead discovery -> contact enrichment -> pitch composition -> approval queue.
Enforces T.s Industries unbreakable business rules on all generated pitches.
"""
import logging
from typing import List, Dict, Any, TypedDict, Optional

try:
    from langgraph.graph import StateGraph, END
except ImportError as e:
    logging.warning(f"LangGraph import warning in outreach_agent: {e}.")
    StateGraph = object
    END = "__end__"

from core.memory import memory_manager
from services.llm_factory import llm_factory
from tools.lead_finder import search_businesses_without_websites, find_contact_email
from tools.procedural_tools import load_unbreakable_rules
from agents.human_approval import PENDING_APPROVAL_QUEUE

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


PITCH_SYSTEM_PROMPT = """
You are an expert sales copywriter for T.s Industries.
Write a concise, friendly, and personalized cold outreach email to a local business owner.
The email should:
- Address the business owner by their business name.
- Empathize with the challenge of being invisible online.
- Highlight a clear value proposition: professional website + local SEO + mobile-first design.
- Include a clear CTA: "Reply to this email to claim your free 30-minute strategy call or request a custom quotation on ts-industries.co.za."
- Include T.s Industries contact email (pharezsigasa@gmail.com) and phone (+447544357979).
- Be under 120 words, professional but warm, short punchy paragraphs. Never use em dashes (—).

Return ONLY the email body text, no subject line.
"""


async def find_leads_node(state: OutreachState) -> OutreachState:
    """
    Node 1: Searches for businesses without websites and populates state['leads'].
    """
    location = state.get("location", "Atlanta, GA")
    industry = state.get("industry", "local services")
    logger.info(f"[OutreachGraph] find_leads_node: location='{location}', industry='{industry}'")

    leads = await search_businesses_without_websites(location=location, industry=industry, limit=10)
    logger.info(f"[OutreachGraph] Found {len(leads)} leads without websites.")

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
            location=location or lead.get("address", "")
        )
        enriched.append({**lead, **contact_info})

    logger.info(f"[OutreachGraph] Enrichment complete. {len(enriched)} leads with contact data.")
    return {**state, "enriched_leads": enriched, "sender": "enrich_leads_node"}


async def compose_pitch_node(state: OutreachState) -> OutreachState:
    """
    Node 3: Generates personalized pitch emails using Gemini + unbreakable rules context.
    """
    enriched = state.get("enriched_leads", [])
    logger.info(f"[OutreachGraph] compose_pitch_node: drafting {len(enriched)} pitch emails...")

    # Load unbreakable rules dynamically
    rules_text = load_unbreakable_rules()
    combined_system = f"CRITICAL CONSTRAINTS:\n{rules_text}\n\n{PITCH_SYSTEM_PROMPT}".strip()

    # Pull portfolio and case study context from memory store
    portfolio_context = await memory_manager.search_memory(
        query="web development portfolio project case study agency", limit=3
    )
    context_text = " ".join([str(c.get("value", {}).get("content", "")) for c in portfolio_context])

    drafted: List[Dict[str, Any]] = []
    for lead in enriched:
        biz_name = lead.get("name", "Your Business")
        email_addr = lead.get("email", "")

        prompt = (
            f"Business: {biz_name}\n"
            f"Location: {lead.get('address', '')}\n"
            f"Agency context: {context_text[:300]}\n"
            f"Write a personalized pitch email for {biz_name}."
        )

        try:
            body = await llm_factory.invoke_drafter(prompt, combined_system)
        except Exception as e:
            logger.warning(f"LLM pitch generation failed for '{biz_name}': {e}")
            body = (
                f"Hi {biz_name} team,\n\n"
                f"We help local businesses get a professional online presence quickly and affordably. "
                f"If you are ready to attract more customers online, reply or visit ts-industries.co.za to set up a strategy call.\n\n"
                f"Best,\nT.s Industries Team\npharezsigasa@gmail.com | +447544357979"
            )

        drafted.append({
            "business_name": biz_name,
            "recipient_email": email_addr,
            "subject": f"Quick question about {biz_name}'s online presence",
            "body": body,
            "lead_data": lead
        })

    logger.info(f"[OutreachGraph] {len(drafted)} pitch emails composed.")
    return {**state, "drafted_pitches": drafted, "sender": "compose_pitch_node"}


async def outreach_dispatcher_node(state: OutreachState) -> OutreachState:
    """
    Node 4: Places drafted pitch emails into the human approval queue for review before sending.
    """
    pitches = state.get("drafted_pitches", [])
    logger.info(f"[OutreachGraph] outreach_dispatcher_node: queuing {len(pitches)} pitches for approval...")

    for pitch in pitches:
        thread_id = f"outreach_{pitch.get('business_name', 'lead').replace(' ', '_').lower()}"
        PENDING_APPROVAL_QUEUE[thread_id] = {
            "thread_id": thread_id,
            "intent": "sales",
            "email_input": {
                "sender": pitch.get("recipient_email"),
                "subject": pitch.get("subject"),
                "body": pitch.get("body"),
            },
            "draft_response": pitch.get("body"),
            "status": "pending",
            "created_at": "Just now",
            "lead_data": pitch.get("lead_data", {})
        }

    summary = (
        f"✅ {len(pitches)} personalized outreach email(s) drafted and placed in the Approval Queue.\n"
        f"Go to the Admin Dashboard > Approval Queue to review and send them."
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
