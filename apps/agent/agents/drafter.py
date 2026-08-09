"""
Drafter Agent Node: Synthesizes responses using Gemini 1.5 Pro, T.S Industries knowledge base, and retrieved vector memories.
"""
import logging
from core.state import AgentState
from services.llm_factory import llm_factory
from core.memory import memory_manager

logger = logging.getLogger("agent.node.drafter")

DRAFTER_SYSTEM_PROMPT = """
You are the official representative of T.S Industries, a high-performance software engineering firm specializing in Web Development (Next.js, React, Tailwind CSS, Python, C#, VB.Net), Mobile Apps (React Native, Java), and AI/Backend Integrations (Supabase, pgvector, LangGraph).

Follow these core directives strictly:
1. Speak as a representative of T.S Industries. Never say "I am an AI."
2. Always drive traffic to the website ts-industries.co.za for more details, portfolio showcases, or case studies.
3. Never quote exact pricing. Encourage the client to book a discovery call or request a formal quotation.
4. Maintain a professional yet approachable tone.
5. Use short, punchy paragraphs and bullet points. Never use em dashes (—).
"""

async def drafter_node(state: AgentState) -> AgentState:
    """
    Drafter Node function for deep reasoning and response drafting.
    """
    logger.info("Executing Drafter Node for T.S Industries...")
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

Please generate a detailed, polished response or draft message representing T.S Industries.
"""

    draft_output = await llm_factory.invoke_drafter(prompt, DRAFTER_SYSTEM_PROMPT)

    return {
        **state,
        "sender": "drafter",
        "draft_response": draft_output,
        "final_output": draft_output
    }
