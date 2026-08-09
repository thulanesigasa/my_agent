"""
Drafter Agent Node: Synthesizes responses using Gemini 1.5 Pro and retrieved vector memories.
"""
import logging
from core.state import AgentState
from services.llm_factory import llm_factory
from core.memory import memory_manager

logger = logging.getLogger("agent.node.drafter")

DRAFTER_SYSTEM_PROMPT = """
You are an expert AI Drafter Node powered by Gemini 1.5 Pro long-context reasoning.
Synthesize the user request, intent category, and retrieved past memories into a comprehensive, accurate, and professional response or communication draft.
"""

async def drafter_node(state: AgentState) -> AgentState:
    """
    Drafter Node function for deep reasoning and response drafting.
    """
    logger.info("Executing Drafter Node...")
    messages = state.get("messages", [])
    intent = state.get("intent", "general")
    email_input = state.get("email_input")
    context = state.get("retrieved_context", [])

    user_input = ""
    if email_input and isinstance(email_input, dict):
        user_input = f"Subject: {email_input.get('subject', '')}\nBody: {email_input.get('body', '')}"
    elif messages:
        last_msg = messages[-1]
        user_input = last_msg.get("content", "") if isinstance(last_msg, dict) else str(getattr(last_msg, "content", last_msg))

    # Additional query if context empty
    if not context:
        context = await memory_manager.search_memory(user_input, limit=3)

    context_str = "\n".join([f"- {c['content']}" for c in context]) if context else "No prior memory context."

    prompt = f"""
Current Intent: {intent}
User Request:
{user_input}

Retrieved Memory Context:
{context_str}

Please generate a detailed, polished response or draft message.
"""

    draft_output = await llm_factory.invoke_drafter(prompt, DRAFTER_SYSTEM_PROMPT)

    return {
        **state,
        "sender": "drafter",
        "draft_response": draft_output,
        "final_output": draft_output
    }
