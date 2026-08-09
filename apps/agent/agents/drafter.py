import logging
from core.state import AgentState
from services.llm_factory import llm_factory

logger = logging.getLogger("agent.node.drafter")

DRAFTER_SYSTEM_PROMPT = """
You are the Drafter Agent node powered by Gemini 1.5 Pro.
You possess long-context understanding, high-reasoning capability, and creative writing skills.
Synthesize retrieved user memories, active intent, and context to compose structured, highly accurate, and helpful responses or draft communications.
"""

async def drafter_node(state: AgentState) -> AgentState:
    """
    Drafter Node: Gemini 1.5 Pro for deep reasoning, response drafting, and synthesis.
    """
    logger.info("Executing Drafter Node...")
    messages = state.get("messages", [])
    intent = state.get("intent", "general_qa")
    memories = state.get("retrieved_memory", [])
    proposed_action = state.get("proposed_action", {})

    user_input = ""
    if messages:
        last_msg = messages[-1]
        user_input = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

    memory_str = "\n".join([f"- {m['content']}" for m in memories]) if memories else "No prior memory context."

    prompt = f"""
Current Active Intent: {intent}
User Request: {user_input}

Retrieved Long-term Context:
{memory_str}

Proposed External Tool Details:
{proposed_action}

Synthesize a comprehensive, polished response or action proposal for the user.
"""

    draft_output = await llm_factory.call_gemini(prompt, DRAFTER_SYSTEM_PROMPT, temperature=0.6)

    return {
        **state,
        "draft_response": draft_output,
        "active_node": "drafter_node"
    }
