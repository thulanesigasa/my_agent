"""
LangGraph Multi-Agent Workflow State Machine.
Orchestrates Triage (Groq), Human Approval Gate, Drafter (Gemini), and Learner (Supabase pgvector) nodes.
"""
import logging
from typing import Literal

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError as e:
    logging.warning(f"LangGraph import warning: {e}. Please run `pip install -r requirements.txt`.")
    # Fallback dummy definitions for static linting environments
    StateGraph = object
    END = "__end__"
    MemorySaver = object

from core.state import AgentState
from agents.triage import triage_node
from agents.drafter import drafter_node
from agents.learner import learner_node

logger = logging.getLogger("agent.graph")


async def human_approval_node(state: AgentState) -> AgentState:
    """
    Human-in-the-Loop Approval Gate:
    Halts execution or flags high-risk actions (e.g. client inquiries, sensitive email dispatch) for approval.
    """
    logger.info("Executing Human Approval Node...")
    status = state.get("approval_status")
    intent = state.get("intent", "general")

    if status == "approved":
        logger.info("Human Approval Granted! Proceeding to Drafter Node.")
        return {
            **state,
            "sender": "human_approval",
            "needs_human_approval": False
        }

    logger.info("Flagging action as pending human approval.")
    return {
        **state,
        "sender": "human_approval",
        "approval_status": "pending",
        "draft_response": f"⚠️ Action flagged for Human Approval. Intent: '{intent}'. Approval pending."
    }


def route_after_triage(state: AgentState) -> Literal["__end__", "human_approval", "drafter"]:
    """
    Conditional Routing logic after Triage Node:
    - If intent == 'spam', route to END.
    - If needs_human_approval is True and not approved, route to human_approval node.
    - Otherwise, route to drafter node.
    """
    intent = state.get("intent", "general")
    needs_approval = state.get("needs_human_approval", False)
    approval_status = state.get("approval_status")

    if intent == "spam":
        logger.info("Routing spam intent to END.")
        return END

    if needs_approval and approval_status != "approved":
        logger.info("Routing sensitive request to human_approval gate node.")
        return "human_approval"

    return "drafter"


def build_agent_graph(checkpointer: Any = None) -> StateGraph:
    """
    Constructs and compiles the StateGraph workflow with nodes, conditional edges, and checkpointer.
    """
    if StateGraph is object:
        logger.error("LangGraph is not installed. Install dependencies using: pip install -r requirements.txt")
        return None

    builder = StateGraph(AgentState)

    # 1. Register Nodes
    builder.add_node("triage", triage_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("drafter", drafter_node)
    builder.add_node("learner", learner_node)

    # 2. Set Entry Point
    builder.set_entry_point("triage")

    # 3. Add Conditional Edges from Triage
    builder.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            END: END,
            "human_approval": "human_approval",
            "drafter": "drafter"
        }
    )

    # 4. Add Node Edges
    builder.add_edge("human_approval", "drafter")
    builder.add_edge("drafter", "learner")
    builder.add_edge("learner", END)

    # 5. Compile with MemorySaver Checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)


# Compiled Agent Workflow Graph instance
checkpointer_instance = MemorySaver() if MemorySaver is not object else None
agent_workflow = build_agent_graph(checkpointer=checkpointer_instance)
