"""
Triage Agent Node: Classifies incoming user messages or emails into intent categories for T.S Industries.
Uses runtime dynamic reading of knowledge/*.md files.
"""
import json
import logging
from core.state import AgentState
from services.llm_factory import llm_factory
from core.memory import memory_manager
from tools.knowledge_tools import read_company_knowledge

logger = logging.getLogger("agent.node.triage")

TRIAGE_SYSTEM_PROMPT = """
You are an expert Triage Agent representing T.S Industries, a high-performance software engineering firm led by Pharez (Thulane).

Analyze incoming user messages or email inputs and classify them into one of these intents:
- "knowledge_update": Admin or user teaching a new fact, rule, tech stack capability, service offering, or business guideline for T.S Industries.
- "sales": Inquiries regarding pricing, quotes, product upgrades, or project scope.
- "support": Bug reports, platform issues, or technical help requests.
- "client_inquiry": High-priority client questions, contract requests, or custom engineering work.
- "general": General questions, greeting, or status checks.
- "spam": Unsolicited promotional mail, irrelevant text, or noise.

Directives:
1. Always represent T.S Industries.
2. Flag "needs_human_approval" as true ONLY if intent is "client_inquiry" or involves sending sensitive communications.

Respond strictly with a JSON object matching:
{
    "intent": "knowledge_update|sales|support|client_inquiry|general|spam",
    "needs_human_approval": true|false,
    "reason": "<brief justification>"
}
"""

async def triage_node(state: AgentState) -> AgentState:
    """
    Triage Node function for intent classification and initial context routing.
    Dynamically loads knowledge/*.md files at runtime for every task.
    """
    logger.info("Executing Triage Node for T.S Industries...")
    messages = state.get("messages", [])
    email_input = state.get("email_input")

    # Read company knowledge dynamically at runtime for this specific execution
    company_knowledge = read_company_knowledge()

    input_text = ""
    if email_input and isinstance(email_input, dict):
        input_text = f"Subject: {email_input.get('subject', '')}\nFrom: {email_input.get('sender', '')}\nBody: {email_input.get('body', '')}"
    elif messages:
        last_msg = messages[-1]
        input_text = last_msg.get("content", "") if isinstance(last_msg, dict) else str(getattr(last_msg, "content", last_msg))

    # Recall relevant context memories
    memories = await memory_manager.search_memory(input_text, limit=3)

    combined_system = f"{company_knowledge}\n\n{TRIAGE_SYSTEM_PROMPT}".strip()
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
        if "remember that" in text_lower or "update knowledge" in text_lower or "new service" in text_lower or "we now offer" in text_lower:
            intent = "knowledge_update"
        elif "client" in text_lower or "contract" in text_lower:
            intent = "client_inquiry"
            needs_approval = True

    # Sensitive client inquiries always trigger human approval gate
    if intent == "client_inquiry":
        needs_approval = True

    return {
        **state,
        "sender": "triage",
        "intent": intent,
        "needs_human_approval": needs_approval,
        "retrieved_context": memories
    }
