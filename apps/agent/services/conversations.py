"""Operator chat archive shared by text and voice. No public-caller commands."""

import re
from uuid import uuid4
from core.store import store


def history(thread_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", thread_id):
        raise ValueError("Invalid conversation ID")
    return store.get("operator_conversations", thread_id) or {
        "id": thread_id,
        "messages": [],
    }


async def run_turn(workflow, text, thread_id, email_input=None):
    owner = uuid4().hex
    key = "operator-turn:" + thread_id
    history(thread_id)
    store.acquire_lease(key, owner, seconds=300)
    try:
        previous = history(thread_id)["messages"]
        # This archive is operator content, never email/call-supplied instructions.
        context = "\n".join(f"{m['role']}: {m['text']}" for m in previous[-12:])[
            -16000:
        ]
        result = await workflow.ainvoke(
            {
                "messages": [{"role": "user", "content": text}],
                "conversation_context": context,
                "email_input": email_input,
                "approval_status": "none",
                "needs_human_approval": False,
            },
            config={"configurable": {"thread_id": thread_id}},
        )
        output = str(
            result.get("final_output")
            or result.get("draft_response")
            or "Request processed."
        )
        turns = previous + [
            {"id": uuid4().hex, "role": "user", "text": text},
            {"id": uuid4().hex, "role": "assistant", "text": output},
        ]
        store.put("operator_conversations", thread_id, {"messages": turns[-100:]})
        return result
    finally:
        store.release_lease(key, owner)
