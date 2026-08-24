"""
LangGraph Multi-Agent Workflow State Machine.
Orchestrates Triage (Groq), Risk Evaluator (Guardrails & Risk Classification), Knowledge Manager, Skill Learner,
Admin Tools, Human Approval Gate (with native LangGraph interrupt_before breakpoints), Drafter (Gemini), Learner, and Outreach.
"""
import logging
import re
from typing import Literal, Any

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError as e:
    logging.warning(f"LangGraph import warning: {e}. Please run `pip install -r requirements.txt`.")
    StateGraph = object
    END = "__end__"
    MemorySaver = object

from core.state import AgentState
from agents.triage import triage_node
from agents.risk_evaluator import risk_evaluator_node
from agents.drafter import drafter_node
from agents.learner import learner_node
from agents.knowledge_manager import knowledge_updater_node
from agents.skill_learner import skill_learner_node
from agents.human_approval import human_approval_node
from tools.admin_tools import unlearn_memory, get_sent_emails

logger = logging.getLogger("agent.graph")


# ── Deferred sub-graph import to avoid circular deps ──────────────────
_outreach_workflow = None

def _get_outreach_workflow():
    global _outreach_workflow
    if _outreach_workflow is None:
        try:
            from agents.outreach_agent import outreach_workflow
            _outreach_workflow = outreach_workflow
        except Exception as e:
            logger.warning(f"Outreach sub-graph unavailable: {e}")
    return _outreach_workflow


# ── Admin Tool Dispatch Node ──────────────────────────────────────────
async def admin_tools_node(state: AgentState) -> AgentState:
    """
    Admin Tools Node: Executes conversational admin commands (unlearn / get emails).
    Triggered when triage detects admin_command intent.
    """
    logger.info("Executing Admin Tools Node...")
    messages = state.get("messages", [])
    last_msg = ""
    if messages:
        m = messages[-1]
        last_msg = m.get("content", "") if isinstance(m, dict) else str(getattr(m, "content", m))

    text_lower = last_msg.lower()
    result = ""

    if "unlearn" in text_lower or "forget" in text_lower or "delete memory" in text_lower:
        match = re.search(r"(?:unlearn|forget|delete memory about?)\s+(.+)", text_lower)
        query = match.group(1).strip() if match else last_msg
        delete_all = "all" in text_lower and "memory" in text_lower
        result = await unlearn_memory(query=query, delete_all=delete_all)

    elif "sent email" in text_lower or "show emails" in text_lower or "email history" in text_lower:
        limit_match = re.search(r"(\d+)\s+email", text_lower)
        limit = int(limit_match.group(1)) if limit_match else 5
        result = await get_sent_emails(limit=limit)

    else:
        result = "ℹ️ Admin tool triggered but no specific command recognized. Try 'unlearn X', 'show last 5 emails', or 'wipe all memory'."

    return {
        **state,
        "sender": "admin_tools",
        "final_output": result,
        "needs_human_approval": False
    }


# ── Outreach Bridge Node ──────────────────────────────────────────────
async def outreach_bridge_node(state: AgentState) -> AgentState:
    """
    Outreach Bridge Node: Extracts location/industry from user message and invokes the outreach sub-graph.
    """
    logger.info("Executing Outreach Bridge Node...")
    messages = state.get("messages", [])
    last_msg = ""
    if messages:
        m = messages[-1]
        last_msg = m.get("content", "") if isinstance(m, dict) else str(getattr(m, "content", m))

    location_match = re.search(r"in ([A-Za-z\s,]+?)(?:\s+without|\s+with|\s+that|\s+for|$)", last_msg, re.IGNORECASE)
    industry_match = re.search(r"(?:find|search|look for)\s+([a-zA-Z\s]+?)(?:\s+in\s|\s+near\s|$)", last_msg, re.IGNORECASE)

    location = location_match.group(1).strip() if location_match else "local area"
    industry = industry_match.group(1).strip() if industry_match else "local businesses"

    outreach_wf = _get_outreach_workflow()
    if outreach_wf is None:
        return {**state, "sender": "outreach_bridge", "final_output": "⚠️ Outreach sub-graph is unavailable. Check LangGraph installation."}

    try:
        outreach_state = await outreach_wf.ainvoke({"location": location, "industry": industry})
        summary = outreach_state.get("outreach_status", "Outreach pipeline executed.")
    except Exception as e:
        logger.error(f"Outreach sub-graph invocation error: {e}")
        summary = f"❌ Outreach pipeline error: {e}"

    return {**state, "sender": "outreach_bridge", "final_output": summary, "needs_human_approval": False}


# ── Routing Logic ─────────────────────────────────────────────────────
def route_after_triage(state: AgentState) -> Literal["__end__", "risk_evaluator", "skill_learner", "knowledge_updater", "admin_tools", "outreach_bridge"]:
    """
    Conditional routing after Triage Node:
    - spam → END
    - skill_learning → skill_learner
    - knowledge_update → knowledge_updater
    - admin_command → admin_tools
    - lead_generation / outreach → outreach_bridge
    - default → risk_evaluator
    """
    intent = state.get("intent", "general")

    if intent == "spam":
        logger.info("Routing spam intent to END.")
        return END

    if intent == "skill_learning":
        logger.info("Routing skill learning request to skill_learner node.")
        return "skill_learner"

    if intent == "knowledge_update":
        logger.info("Routing knowledge update request to knowledge_updater node.")
        return "knowledge_updater"

    if intent == "admin_command":
        logger.info("Routing admin command to admin_tools node.")
        return "admin_tools"

    if intent in ("lead_generation", "outreach"):
        logger.info("Routing lead generation request to outreach_bridge node.")
        return "outreach_bridge"

    return "risk_evaluator"


def route_after_risk_evaluator(state: AgentState) -> Literal["__end__", "human_approval", "drafter"]:
    """
    Conditional routing after Risk Evaluator Node:
    - FORBIDDEN action → END
    - HIGH risk action (needs_human_approval=True) → human_approval
    - LOW risk action → drafter
    """
    is_forbidden = state.get("is_forbidden", False)
    needs_approval = state.get("needs_human_approval", False)
    approval_status = state.get("approval_status")

    if is_forbidden:
        logger.warning("Routing FORBIDDEN action to END.")
        return END

    if needs_approval and approval_status != "approved":
        logger.info("Routing HIGH-risk action to human_approval gate node.")
        return "human_approval"

    return "drafter"


# ── Graph Builder ─────────────────────────────────────────────────────
def build_agent_graph(checkpointer: Any = None) -> Any:
    """
    Constructs and compiles the full StateGraph with risk evaluator, native interrupt_before breakpoints,
    skill learner, knowledge updater, admin tools, and outreach sub-graph routing.
    """
    if StateGraph is object:
        logger.error("LangGraph is not installed. Install dependencies using: pip install -r requirements.txt")
        return None

    builder = StateGraph(AgentState)

    # Register Nodes
    builder.add_node("triage", triage_node)
    builder.add_node("risk_evaluator", risk_evaluator_node)
    builder.add_node("skill_learner", skill_learner_node)
    builder.add_node("knowledge_updater", knowledge_updater_node)
    builder.add_node("admin_tools", admin_tools_node)
    builder.add_node("outreach_bridge", outreach_bridge_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("drafter", drafter_node)
    builder.add_node("learner", learner_node)

    # Set Entry Point
    builder.set_entry_point("triage")

    # Conditional Routing from Triage
    builder.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            END: END,
            "risk_evaluator": "risk_evaluator",
            "skill_learner": "skill_learner",
            "knowledge_updater": "knowledge_updater",
            "admin_tools": "admin_tools",
            "outreach_bridge": "outreach_bridge",
        }
    )

    # Conditional Routing from Risk Evaluator
    builder.add_conditional_edges(
        "risk_evaluator",
        route_after_risk_evaluator,
        {
            END: END,
            "human_approval": "human_approval",
            "drafter": "drafter"
        }
    )

    # Edge connections
    builder.add_edge("skill_learner", END)
    builder.add_edge("knowledge_updater", END)
    builder.add_edge("admin_tools", END)
    builder.add_edge("outreach_bridge", END)
    builder.add_edge("human_approval", "drafter")
    builder.add_edge("drafter", END)
    builder.add_edge("learner", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    # Native LangGraph breakpoint interrupt before high-stakes human approval node
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"]
    )


# Compiled Agent Workflow Graph instance with native interrupt_before breakpoint
checkpointer_instance = MemorySaver() if MemorySaver is not object else None
agent_workflow = build_agent_graph(checkpointer=checkpointer_instance)
