"""
Conversational Admin Control Tools.
LangChain @tool-decorated functions for voice-driven memory management and email history retrieval.
"""

import logging
from core.memory import memory_manager

logger = logging.getLogger("agent.tools.admin")


async def unlearn_memory(query: str = "", delete_all: bool = False) -> str:
    """
    Unlearn memory records from Supabase langgraph_memory store.

    Args:
        query: Semantic query to find and delete matching memory records.
        delete_all: If True, wipes all memory records in the active scope.

    Returns:
        Confirmation string summarizing what was removed.
    """
    logger.info(f"unlearn_memory called [delete_all={delete_all}, query='{query}']")

    if not memory_manager.client:
        from core.store import store

        words = set(query.lower().split())
        records = store.list("memories")
        selected = [
            m
            for m in records
            if delete_all or words.intersection(str(m.get("value", {})).lower().split())
        ]
        for record in selected:
            store.delete("memories", record["id"])
        return f"[SUCCESS] Removed {len(selected)} persisted local memory record(s)."

    try:
        if delete_all:
            memory_manager.client.table("langgraph_memory").delete().neq(
                "id", ""
            ).execute()
            return "[SUCCESS] All memory records wiped from langgraph_memory store."

        # Semantic search then delete matching records
        matches = await memory_manager.search_past_interactions(
            query=query, user_id="default_user", limit=10
        )
        if not matches:
            return f"[INFO] No memory records found matching '{query}'. Nothing was deleted."

        deleted_summaries = []
        for record in matches:
            record_id = record.get("id")
            content = record.get("value", {})
            if record_id:
                memory_manager.client.table("langgraph_memory").delete().eq(
                    "id", record_id
                ).execute()
                deleted_summaries.append(str(content)[:60])

        return (
            f"[SUCCESS] Removed {len(deleted_summaries)} memory record(s) matching '{query}':\n"
            + "\n".join(f"  – {s}" for s in deleted_summaries)
        )
    except Exception as e:
        logger.error(f"Error in unlearn_memory: {e}")
        return f"[ERROR] Memory unlearn failed: {e}"


async def get_sent_emails(limit: int = 5) -> str:
    """
    Retrieves recently sent emails from Gmail API or local logs.

    Args:
        limit: Maximum number of recent emails to return.

    Returns:
        Formatted string summary of subjects, recipients, and timestamps.
    """
    logger.info(f"get_sent_emails called [limit={limit}]")
    from core.store import store

    emails = store.email_logs()[-limit:]
    if not emails:
        return "[OUTBOX] No confirmed outreach sends recorded."
    return "\n".join(
        f"To: {m['recipient']} | Subject: {m['subject']} | Sent: {m['dateSent']}"
        for m in emails
    )
