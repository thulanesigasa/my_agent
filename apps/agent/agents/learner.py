"""
Learner Agent Node: Extracts permanent facts (client preferences, business rules, context) and persists them via memory_manager.put().
"""
import logging
import hashlib
from core.state import AgentState
from core.memory import memory_manager
from services.llm_factory import llm_factory

logger = logging.getLogger("agent.node.learner")

LEARNER_SYSTEM_PROMPT = """
You are an expert Continuous Learning Node.
Analyze the conversation messages and extract ONLY new, permanent facts, client preferences, business rules, or key user context.
Ignore conversational filler, greetings, and temporary statements.
Return ONLY bullet points of distinct permanent facts to store, or 'NONE' if no meaningful facts were present.
"""


async def learner_node(state: AgentState) -> AgentState:
    """
    Learner Node function for automated insight extraction and vector memory indexing via BaseStore.put().
    """
    logger.info("Executing Learner Node...")
    messages = state.get("messages", [])
    draft_response = state.get("draft_response", "")
    email_input = state.get("email_input") or {}

    user_id = email_input.get("sender", "default_user")
    thread_id = email_input.get("thread_id", "session_001")

    if not messages and not draft_response:
        return {**state, "sender": "learner"}

    user_text = ""
    if messages:
        last_msg = messages[-1]
        user_text = last_msg.get("content", "") if isinstance(last_msg, dict) else str(getattr(last_msg, "content", last_msg))

    prompt = f"User Input: {user_text}\nResponse Context: {draft_response}"
    extraction = await llm_factory.invoke_triage(prompt, LEARNER_SYSTEM_PROMPT)

    learnings = []
    if extraction and "NONE" not in extraction.upper():
        lines = [line.strip("- ").strip() for line in extraction.split("\n") if line.strip()]
        for fact in lines:
            if len(fact) > 5 and not fact.startswith("{"):
                learnings.append(fact)
                fact_key = hashlib.md5(fact.encode("utf-8")).hexdigest()[:12]
                
                # Persist to langgraph_memory via store.put()
                await memory_manager.put(
                    namespace=("users", user_id, "memories"),
                    key=fact_key,
                    value={
                        "content": fact,
                        "thread_id": thread_id,
                        "intent": state.get("intent", "general"),
                        "source": "learner_node"
                    }
                )

    logger.info(f"Learner node persisted {len(learnings)} permanent facts into memory store.")

    return {
        **state,
        "sender": "learner",
        "extracted_learnings": learnings
    }
