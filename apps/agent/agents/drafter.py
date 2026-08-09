"""
Drafter Agent Node: Synthesizes responses using Gemini 1.5 Pro, T.s Industries knowledge base,
unbreakable business rules, and procedural skills.
"""
import logging
from core.state import AgentState
from services.llm_factory import llm_factory
from core.memory import memory_manager
from tools.knowledge_tools import read_company_knowledge
from tools.procedural_tools import load_unbreakable_rules, fetch_skill

logger = logging.getLogger("agent.node.drafter")

DRAFTER_SYSTEM_PROMPT = """
You are the official representative of T.s Industries, a high-performance software engineering firm specializing in Web Development, Mobile Apps, and AI/Backend Integrations.

Follow these core directives strictly:
1. Speak as a representative of T.s Industries. Never say "I am an AI."
2. Always drive traffic to the website ts-industries.co.za for more details, portfolio showcases, or case studies.
3. Never quote exact pricing without established scope. Encourage booking a discovery call.
4. Maintain a professional yet approachable tone.
5. Use short, punchy paragraphs and bullet points. Never use em dashes (—).
"""

async def drafter_node(state: AgentState) -> AgentState:
    """
    Drafter Node function for deep reasoning, skill execution, and response drafting.
    Dynamically loads knowledge/*.md, unbreakable rules, and procedural skills at runtime.
    """
    logger.info("Executing Drafter Node for T.s Industries...")
    messages = state.get("messages", [])
    intent = state.get("intent", "general")
    email_input = state.get("email_input")
    context = state.get("retrieved_context", [])

    # Read company knowledge dynamically at runtime
    company_knowledge = read_company_knowledge()

    # Load unbreakable rules and procedural skills
    unbreakable_rules = load_unbreakable_rules()

    user_input = ""
    if email_input and isinstance(email_input, dict):
        user_input = f"Subject: {email_input.get('subject', '')}\nBody: {email_input.get('body', '')}"
    elif messages:
        last_msg = messages[-1]
        user_input = last_msg.get("content", "") if isinstance(last_msg, dict) else str(getattr(last_msg, "content", last_msg))

    # Fetch matching procedural skill if applicable (e.g. quote, onboarding)
    task_keyword = "quote" if "quote" in user_input.lower() or "pricing" in user_input.lower() else intent
    skill_procedure = fetch_skill(task_keyword)

    # Additional query if context empty
    if not context:
        context = await memory_manager.search_memory(user_input, limit=3)

    context_str = "\n".join([f"- {c['content']}" for c in context]) if context else "No prior memory context."

    combined_system = f"""
{company_knowledge}

CRITICAL CONSTRAINTS:
{unbreakable_rules}

{DRAFTER_SYSTEM_PROMPT}
""".strip()

    prompt = f"""
Current Intent: {intent}
User Request:
{user_input}

{skill_procedure}

Retrieved Memory Context:
{context_str}

Please generate a detailed, polished response or draft message representing T.s Industries following all procedures and critical constraints.
"""

    draft_output = await llm_factory.invoke_drafter(prompt, combined_system)

    return {
        **state,
        "sender": "drafter",
        "draft_response": draft_output,
        "final_output": draft_output
    }
