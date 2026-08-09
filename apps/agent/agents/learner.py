import logging
from core.state import AgentState
from core.memory import memory_store
from services.llm_factory import llm_factory

logger = logging.getLogger("agent.node.learner")

LEARNER_SYSTEM_PROMPT = """
You are the Continuous Learning & Memory Indexer node.
Extract essential facts, user preferences, project details, or commitments from the conversation turn.
Return ONLY bullet points of new facts to remember, or 'NONE' if no new information was presented.
"""

async def learner_node(state: AgentState) -> AgentState:
    """
    Learner Node: Continuous self-reflection, fact extraction, and Supabase pgvector indexing.
    """
    logger.info("Executing Learner Node...")
    messages = state.get("messages", [])
    draft_response = state.get("draft_response", "")

    if not messages:
        return state

    last_user_msg = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])

    prompt = f"User Message: {last_user_msg}\nAgent Response: {draft_response}"
    extraction = await llm_factory.call_groq(prompt, LEARNER_SYSTEM_PROMPT, temperature=0.1)

    extracted_learnings = []
    if extraction and "NONE" not in extraction.upper():
        lines = [line.strip("- ").strip() for line in extraction.split("\n") if line.strip()]
        for fact in lines:
            if len(fact) > 5:
                extracted_learnings.append(fact)
                await memory_store.save_memory(fact, metadata={"source": "continuous_learning"})

    logger.info(f"Learner node extracted {len(extracted_learnings)} new facts for memory index.")

    return {
        **state,
        "extracted_learnings": extracted_learnings,
        "active_node": "learner_node"
    }
