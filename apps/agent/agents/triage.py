import json
import logging
from core.state import AgentState
from services.llm_factory import llm_factory
from core.memory import memory_store

logger = logging.getLogger("agent.node.triage")

TRIAGE_SYSTEM_PROMPT = """
You are the Triage Agent node in an autonomous multi-agent platform powered by Groq Llama 3.3 70B.
Your task is to analyze user messages, categorize intent, query relevant long-term memory, and decide routing.

Intents:
- "email_dispatch": Creating or sending emails (requires human approval if sending).
- "whatsapp_dispatch": Messaging via WhatsApp (requires human approval).
- "draft_response": Complex reasoning, project planning, drafting documents.
- "general_qa": Quick answers, conversation, status inquiries.

Respond ONLY with a valid JSON object matching this schema:
{
    "intent": "<email_dispatch|whatsapp_dispatch|draft_response|general_qa>",
    "requires_human_approval": true|false,
    "reason": "<brief justification>",
    "action_payload": {"recipient": "...", "subject": "...", "body": "..."} // if email/whatsapp
}
"""

async def triage_node(state: AgentState) -> AgentState:
    """
    Triage Node: Fast intent classification using Groq Llama 3.3 70B & memory lookup.
    """
    logger.info("Executing Triage Node...")
    messages = state.get("messages", [])
    user_input = ""
    if messages:
        last_msg = messages[-1]
        user_input = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

    # 1. Recall memory from Supabase pgvector
    memories = await memory_store.recall_memories(user_input, limit=3)
    memory_context = "\n".join([f"- {m['content']}" for m in memories])

    # 2. Call Groq for fast triage analysis
    prompt = f"User Input: {user_input}\n\nRetrieved Long-term Memories:\n{memory_context}"
    llm_output = await llm_factory.call_groq(prompt, TRIAGE_SYSTEM_PROMPT, temperature=0.1)

    intent = "general_qa"
    requires_approval = False
    action_payload = None

    try:
        # Extract JSON from output
        start_idx = llm_output.find("{")
        end_idx = llm_output.rfind("}")
        if start_idx != -1 and end_idx != -1:
            parsed = json.loads(llm_output[start_idx:end_idx + 1])
            intent = parsed.get("intent", "general_qa")
            requires_approval = parsed.get("requires_human_approval", False)
            action_payload = parsed.get("action_payload", None)
    except Exception as e:
        logger.warning(f"Triage JSON parsing warning: {e}. Falling back to default heuristics.")
        if "email" in user_input.lower():
            intent = "email_dispatch"
            requires_approval = True
        elif "whatsapp" in user_input.lower():
            intent = "whatsapp_dispatch"
            requires_approval = True

    return {
        **state,
        "intent": intent,
        "retrieved_memory": memories,
        "requires_human_approval": requires_approval,
        "proposed_action": action_payload,
        "active_node": "triage_node"
    }
