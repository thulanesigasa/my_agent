"""
Triage Agent Node: Classifies incoming user messages or emails into intent categories for T.s Industries.
Uses runtime dynamic reading of knowledge/*.md files, unbreakable rules, and procedural skills.
"""
import json
import logging
from core.state import AgentState
from services.llm_factory import llm_factory
from core.memory import memory_manager
from tools.knowledge_tools import read_company_knowledge
from tools.procedural_tools import load_unbreakable_rules, fetch_skill

logger = logging.getLogger("agent.node.triage")

TRIAGE_SYSTEM_PROMPT = """
You are an expert Triage Agent representing T.s Industries, a high-performance software engineering firm led by Pharez (Thulane).

Analyze incoming user messages or email inputs and classify them into one of these intents:
- "skill_learning": User or admin explicitly asking to learn/save a new step-by-step procedure or command (e.g. "learn procedure X", "save skill Y").
- "knowledge_update": User explicitly asking to save or remember a company rule/fact into the knowledge base (e.g. "remember that X", "save rule Y", "update knowledge Z").
- "quote_request": Client requesting pricing estimates, proposals, or project quotations.
- "sales": Inquiries regarding pricing options, product upgrades, or purchase intentions.
- "support": Bug reports, platform issues, or technical help requests.
- "client_inquiry": High-priority client questions, contract requests, or custom engineering work.
- "general": Requests for reports, sending reports, questions, greetings, or general conversation.
- "spam": Unsolicited promotional mail, irrelevant text, or noise.

Directives:
1. If the user asks for a report or asks to send/generate a report or answer a question, classify as "general". DO NOT classify as "knowledge_update" unless the user explicitly tells you to save or remember a new rule into the knowledge base.
2. Flag "needs_human_approval" as true ONLY if intent is "client_inquiry" or involves sending sensitive external communications.

Respond strictly with a JSON object matching:
{
    "intent": "skill_learning|knowledge_update|quote_request|sales|support|client_inquiry|general|spam",
    "needs_human_approval": true|false,
    "reason": "<brief justification>"
}
"""

async def triage_node(state: AgentState) -> AgentState:
    """
    Triage Node function for intent classification and initial context routing.
    Dynamically loads knowledge/*.md and unbreakable rules at runtime for every task.
    """
    logger.info("Executing Triage Node for T.s Industries...")
    messages = state.get("messages", [])
    email_input = state.get("email_input")

    # Read company knowledge and rules dynamically at runtime
    company_knowledge = read_company_knowledge()
    unbreakable_rules = load_unbreakable_rules()

    input_text = ""
    if email_input and isinstance(email_input, dict):
        input_text = f"Subject: {email_input.get('subject', '')}\nFrom: {email_input.get('sender', '')}\nBody: {email_input.get('body', '')}"
    elif messages:
        last_msg = messages[-1]
        input_text = last_msg.get("content", "") if isinstance(last_msg, dict) else str(getattr(last_msg, "content", last_msg))

    # Recall relevant context memories
    memories = await memory_manager.search_memory(input_text, limit=3)

    combined_system = f"""
{company_knowledge}

CRITICAL CONSTRAINTS:
{unbreakable_rules}

{TRIAGE_SYSTEM_PROMPT}
""".strip()

    prompt = f"User Input:\n{input_text}"
    output_str = await llm_factory.invoke_triage(prompt, combined_system)

    intent = "general"
    needs_approval = False

    try:
        start_idx = output_str.find("{")
        end_idx = output_str.rfind("}")
        if start_idx != -1 and end_idx != -1:
            data = json.loads(output_str[start_idx:end_idx + 1])
            intent = data.get("intent", "general")
            needs_approval = data.get("needs_human_approval", False)
    except Exception as e:
        logger.warning(f"Triage JSON extraction warning: {e}")
        text_lower = input_text.lower()
        if "how to" in text_lower or "step by step" in text_lower or "procedure:" in text_lower:
            intent = "skill_learning"
        elif "quote" in text_lower or "pricing" in text_lower or "estimate" in text_lower:
            intent = "quote_request"
        elif "remember that" in text_lower or "update knowledge" in text_lower:
            intent = "knowledge_update"

    # Fetch skill procedure if specific job requested
    if intent in ("quote_request", "sales"):
        skill_text = fetch_skill("quote")
        if skill_text:
            logger.info("Found procedural skill for quote generation.")

    if intent == "client_inquiry":
        needs_approval = True

    return {
        **state,
        "sender": "triage",
        "intent": intent,
        "needs_human_approval": needs_approval,
        "retrieved_context": memories
    }
