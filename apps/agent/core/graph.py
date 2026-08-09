import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.triage import triage_node
from agents.drafter import drafter_node
from agents.learner import learner_node
from services.audio_service import audio_service
from services.email_service import email_service
from services.whatsapp_service import whatsapp_service

logger = logging.getLogger("agent.graph")

async def human_approval_node(state: AgentState) -> AgentState:
    """
    Human-in-the-Loop Approval Gate:
    Flags high-risk external actions (such as sending emails or WhatsApp messages)
    and waits for explicit approval via UI/WebSocket.
    """
    logger.info("Entering Human Approval Gate Node...")
    proposed = state.get("proposed_action") or {}
    intent = state.get("intent", "action")

    # If already approved by user in state
    if state.get("approval_status") == "approved":
        logger.info("Human Approval Granted! Executing external tool action...")
        if intent == "email_dispatch":
            res = await email_service.send_email(
                draft_id="draft_101",
                recipient=proposed.get("recipient", "user@example.com"),
                subject=proposed.get("subject", "Agent Action"),
                body=proposed.get("body", state.get("draft_response", ""))
            )
            state["draft_response"] = f"✅ Action Approved & Executed! Email sent to {res.get('recipient')}."
        elif intent == "whatsapp_dispatch":
            res = await whatsapp_service.send_whatsapp_message(
                recipient_number=proposed.get("recipient", "+1234567890"),
                message_body=proposed.get("body", state.get("draft_response", ""))
            )
            state["draft_response"] = f"✅ Action Approved & Executed! WhatsApp message sent to {res.get('to')}."
        state["requires_human_approval"] = False
        return state

    # Otherwise flag as pending approval
    state["approval_status"] = "pending"
    state["draft_response"] = f"⚠️ High-risk action detected ({intent}). Requesting human approval for details: {proposed}"
    state["active_node"] = "human_approval_node"
    return state


async def output_dispatcher_node(state: AgentState) -> AgentState:
    """
    Output Dispatcher Node:
    Prepares final textual response and generates neural voice TTS payload via Edge-TTS.
    """
    logger.info("Executing Output Dispatcher Node...")
    draft = state.get("draft_response", "Autonomous agent task complete.")

    # Generate TTS voice audio payload
    audio_b64 = await audio_service.text_to_speech_base64(draft[:250])

    return {
        **state,
        "audio_payload": audio_b64,
        "active_node": "output_dispatcher_node"
    }


def route_after_triage(state: AgentState) -> Literal["human_approval_node", "drafter_node"]:
    """
    Conditional Routing Function:
    Routes high-risk tasks requiring approval to Human Approval Gate; otherwise routes directly to Drafter.
    """
    if state.get("requires_human_approval") and state.get("approval_status") != "approved":
        return "human_approval_node"
    return "drafter_node"


def build_agent_graph() -> StateGraph:
    """
    Construct the complete LangGraph state machine flow:
    Triage (Groq) -> Conditional Router -> Drafter (Gemini) -> Learner (Memory Indexer) -> Output Dispatcher
    """
    builder = StateGraph(AgentState)

    # Add State Machine Nodes
    builder.add_node("triage_node", triage_node)
    builder.add_node("human_approval_node", human_approval_node)
    builder.add_node("drafter_node", drafter_node)
    builder.add_node("learner_node", learner_node)
    builder.add_node("output_dispatcher_node", output_dispatcher_node)

    # Set Entry Point
    builder.set_entry_point("triage_node")

    # Conditional Branch after Triage
    builder.add_conditional_edges(
        "triage_node",
        route_after_triage,
        {
            "human_approval_node": "human_approval_node",
            "drafter_node": "drafter_node"
        }
    )

    # Flow Edges
    builder.add_edge("human_approval_node", "drafter_node")
    builder.add_edge("drafter_node", "learner_node")
    builder.add_edge("learner_node", "output_dispatcher_node")
    builder.add_edge("output_dispatcher_node", END)

    return builder.compile()


# Compiled LangGraph Workflow instance
agent_workflow = build_agent_graph()
