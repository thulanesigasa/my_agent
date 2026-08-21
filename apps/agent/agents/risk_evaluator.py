"""
Risk Evaluator Agent Node: Evaluates action risk levels against memory/guardrails.md definitions.
Classifies actions as LOW (Auto-Approve), HIGH (Requires Human Approval), or FORBIDDEN (Halt Execution).
"""
import json
import logging
from pathlib import Path
from core.state import AgentState
from services.llm_factory import llm_factory

logger = logging.getLogger("agent.node.risk_evaluator")


def load_guardrails() -> str:
    """
    Reads memory/guardrails.md and returns the security guidelines.
    """
    module_root = Path(__file__).resolve().parent.parent.parent.parent
    possible_paths = [
        module_root / "memory" / "guardrails.md",
        Path.cwd() / "memory" / "guardrails.md",
        Path.cwd().parent / "memory" / "guardrails.md",
    ]
    for p in possible_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Error reading guardrails at {p}: {e}")

    return (
        "LOW: Read-only search, internal drafts.\n"
        "HIGH: External email, quotes, WhatsApp, memory edits.\n"
        "FORBIDDEN: Payment processing, secret key sharing, spam."
    )


RISK_EVALUATOR_PROMPT = """
You are an expert AI Security Evaluator Node representing T.s Industries.
Your sole job is to evaluate an intended agent action against the security guardrails.

Classify the intended action into one of three risk levels:
- "LOW": Internal searches, lead browsing, public QA, drafting notes. Auto-approve.
- "HIGH": Sending external emails, issuing price quotes, modifying memory files, WhatsApp messaging. Requires human approval.
- "FORBIDDEN": Payments, sharing secret keys/passwords, spamming. Halt immediately.

Respond strictly with a JSON object:
{
    "risk_level": "LOW|HIGH|FORBIDDEN",
    "reason": "<clear justification for classification>",
    "action_summary": "<brief summary of intended action>"
}
"""


async def risk_evaluator_node(state: AgentState) -> AgentState:
    """
    Risk Evaluator Node: Classifies state actions into LOW, HIGH, or FORBIDDEN risk categories.
    """
    logger.info("Executing Risk Evaluator Node...")
    guardrails_text = load_guardrails()
    intent = state.get("intent", "general")
    draft = state.get("draft_response", "")
    messages = state.get("messages", [])

    last_msg = ""
    if messages:
        m = messages[-1]
        last_msg = m.get("content", "") if isinstance(m, dict) else str(getattr(m, "content", m))

    action_context = f"Intent: '{intent}'\nDraft Content: '{draft[:300]}'\nLast User Message: '{last_msg[:300]}'"

    combined_system = f"""
=== SECURITY GUARDRAILS POLICY ===
{guardrails_text}

{RISK_EVALUATOR_PROMPT}
""".strip()

    prompt = f"Action to Evaluate:\n{action_context}"

    risk_level = "LOW"
    reason = "Evaluated default action."

    try:
        output_str = await llm_factory.invoke_triage(prompt, combined_system)
        start_idx = output_str.find("{")
        end_idx = output_str.rfind("}")
        if start_idx != -1 and end_idx != -1:
            data = json.loads(output_str[start_idx:end_idx + 1])
            risk_level = data.get("risk_level", "LOW").upper()
            reason = data.get("reason", reason)
    except Exception as e:
        logger.warning(f"Risk evaluator parsing warning: {e}")
        text_lower = action_context.lower()
        if "payment" in text_lower or "password" in text_lower or "api_key" in text_lower or "secret" in text_lower:
            risk_level = "FORBIDDEN"
        elif intent in ("sales", "client_inquiry", "quote_request") or "send email" in text_lower or "quote" in text_lower:
            risk_level = "HIGH"

    logger.info(f"[RiskEvaluator] Action evaluated as '{risk_level}'. Reason: {reason}")

    if risk_level == "FORBIDDEN":
        error_msg = f"🚫 SECURITY BLOCK: Action forbidden by guardrails policy. Reason: {reason}"
        return {
            **state,
            "sender": "risk_evaluator",
            "risk_level": "FORBIDDEN",
            "needs_human_approval": False,
            "is_forbidden": True,
            "final_output": error_msg,
            "draft_response": error_msg,
        }

    needs_approval = (risk_level == "HIGH")

    return {
        **state,
        "sender": "risk_evaluator",
        "risk_level": risk_level,
        "needs_human_approval": needs_approval,
        "is_forbidden": False,
    }
