"""One persistent inbox claim path for polling and webhooks."""

import json
import logging
from core.store import store, now
from services.email_service import email_service

logger = logging.getLogger("agent.inbox")


async def process_inbox_batch():
    # Lazy import avoids graph -> drafter -> approvals -> service cycles.
    from core.graph import agent_workflow

    messages = await email_service.fetch_unread_emails(max_results=5)
    result = {"processed": 0, "skipped": 0, "failed": 0}
    for mail in messages:
        message_id = mail.get("id")
        if not message_id:
            raise ValueError("Inbox message has no provider ID")
        with store.connect() as db:
            claim = db.execute(
                "INSERT OR IGNORE INTO records VALUES ('inbox', ?, ?)",
                (
                    message_id,
                    json.dumps({**mail, "status": "processing", "created_at": now()}),
                ),
            )
        if not claim.rowcount:
            existing = store.get("inbox", message_id)
            # A retry must not silently acknowledge a previously failed workflow.
            result["failed" if existing["status"] == "failed" else "skipped"] += 1
            continue
        try:
            await agent_workflow.ainvoke(
                {
                    "messages": [{"role": "user", "content": mail.get("body", "")}],
                    "email_input": mail,
                    "approval_status": "none",
                },
                config={"configurable": {"thread_id": f"inbox_{mail['thread_id']}"}},
            )
            store.transition("inbox", message_id, ["processing"], "processed")
            result["processed"] += 1
        except Exception:
            logger.exception("Inbox task failed")
            store.transition(
                "inbox",
                message_id,
                ["processing"],
                "failed",
                error="Workflow failed; manual review needed",
            )
            result["failed"] += 1
    return result
