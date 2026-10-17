"""History sync and a durable pending queue for only tracked conversations."""

import logging
from uuid import uuid4
from config import settings
from core.store import store, ConflictError
from services.contacts import suppress
from services.email_service import email_service

logger = logging.getLogger("agent.inbox")


def match_conversation(mail, mailbox):
    if (
        mail.get("sender") == mailbox
        or "SENT" in mail.get("labels", [])
        or "DRAFT" in mail.get("labels", [])
    ):
        return None
    candidates = [
        m
        for m in store.list("messages")
        if m.get("status") == "sent"
        and m.get("thread_id") == mail.get("thread_id")
        and m.get("from") == mailbox
        and m.get("purpose") in ("outreach", "reply", "test")
        and (m["to"] == mail.get("sender") or mail.get("bounce"))
    ]
    if not candidates:
        return None
    original = next(
        (m for m in candidates if m.get("purpose") in ("outreach", "test")),
        candidates[0],
    )
    return {
        **mail,
        "matched_outbound_id": original["id"],
        "conversation_purpose": "test" if original["purpose"] == "test" else "reply",
    }


async def process_pending(limit=25):
    from core.graph import agent_workflow

    result = {"processed": 0, "skipped": 0, "failed": 0}
    pending = [
        m
        for m in store.list("inbox")
        if m["status"] == "pending" and m.get("mailbox") == email_service.expected_email
    ][:limit]
    for mail in pending:
        try:
            store.transition("inbox", mail["id"], ["pending"], "processing")
        except ConflictError:
            result["skipped"] += 1
            continue
        try:
            if mail.get("unsubscribe") and not mail.get("automated"):
                suppress(mail["sender"], f"Gmail reply {mail['provider_message_id']}")
            if (
                settings.GMAIL_DRAFT_REPLIES
                and not mail.get("automated")
                and not mail.get("unsubscribe")
            ):
                await agent_workflow.ainvoke(
                    {
                        "messages": [{"role": "user", "content": mail["body"]}],
                        "email_input": mail,
                        "approval_status": "none",
                    },
                    config={"configurable": {"thread_id": f"inbox_{mail['id']}"}},
                )
            store.transition("inbox", mail["id"], ["processing"], "processed")
            result["processed"] += 1
        except Exception:
            logger.warning(
                "Reply drafting/processing failed; the incoming message remains recorded"
            )
            store.transition(
                "inbox",
                mail["id"],
                ["processing"],
                "failed",
                error="Processing failed; retry from Gmail settings",
            )
            result["failed"] += 1
    return result


async def process_inbox_batch():
    owner = uuid4().hex
    store.acquire_lease("gmail-sync", owner)
    try:
        cursor = store.get("gmail_cursor", email_service.expected_email or "") or {}
        changed = await email_service.sync_mailbox(
            cursor.get("history_id"), lambda: store.renew_lease("gmail-sync", owner)
        )
        tracked = [
            match_conversation(mail, changed["mailbox"]) for mail in changed["messages"]
        ]
        tracked = [mail for mail in tracked if mail is not None]
        recorded = store.ingest_mailbox(
            owner,
            changed["mailbox"],
            changed["history_id"],
            tracked,
            changed.get("thread_ids", []),
        )
    finally:
        store.release_lease("gmail-sync", owner)
    return {
        **await process_pending(),
        "recorded": recorded,
        "full_sync": changed["full_sync"],
    }
