"""
Learner Agent Node: Extracts key facts, lessons, and preferences and persists them into Supabase pgvector.
"""
import logging
from core.state import AgentState
from core.memory import memory_manager
from services.llm_factory import llm_factory

logger = logging.getLogger("agent.node.learner")

LEARNER_SYSTEM_PROMPT = """
You are a Continuous Learning & Fact Extractor Node.
Extract key business facts, client preferences, project details, or commitments from the interaction.
Return bullet points of distinct new facts, or 'NONE' if no relevant facts are present.
"""

async def learner_node(state: AgentState) -> AgentState:
    """
    Learner Node function for automated fact extraction and memory indexing.
    """
    logger.info("Executing Learner Node...")
    messages = state.get("messages", [])
    draft_response = state.get("draft_response", "")

    if not messages and not draft_response:
        return {**state, "sender": "learner"}

    user_text = ""
    if messages:
        last_msg = messages[-1]
        user_text = last_msg.get("content", "") if isinstance(last_msg, dict) else str(getattr(last_msg, "content", last_msg))

    prompt = f"User Input: {user_text}\nDrafted Response: {draft_response}"
    extraction = await llm_factory.invoke_triage(prompt, LEARNER_SYSTEM_PROMPT)

    learnings = []
    if extraction and "NONE" not in extraction.upper():
        lines = [line.strip("- ").strip() for line in extraction.split("\n") if line.strip()]
        for fact in lines:
            if len(fact) > 5 and not fact.startswith("{"):
                learnings.append(fact)
                await memory_manager.save_memory(fact, metadata={"source": "continuous_learning", "intent": state.get("intent")})

    logger.info(f"Learner node indexed {len(learnings)} new facts into memory store.")

    return {
        **state,
        "sender": "learner",
        "extracted_learnings": learnings
    }
