"""
Conversational Admin Control Tools.
LangChain @tool-decorated functions for voice-driven memory management and email history retrieval.
"""
import logging
from typing import Optional
from core.memory import memory_manager
from services.email_service import email_service

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
        # Fallback: clear in-memory store
        if delete_all:
            count = len(memory_manager._local_memories)
            memory_manager._local_memories.clear()
            return f"[SUCCESS] Cleared all {count} in-memory records (offline mode)."
        else:
            before = len(memory_manager._local_memories)
            query_words = set(query.lower().split())
            memory_manager._local_memories = [
                m for m in memory_manager._local_memories
                if not query_words.intersection(set(str(m.get("value", {})).lower().split()))
            ]
            after = len(memory_manager._local_memories)
            return f"[SUCCESS] Removed {before - after} memory record(s) matching '{query}' (offline mode)."

    try:
        if delete_all:
            res = memory_manager.client.table("langgraph_memory").delete().neq("id", "").execute()
            return "[SUCCESS] All memory records wiped from langgraph_memory store."

        # Semantic search then delete matching records
        matches = await memory_manager.search_past_interactions(query=query, user_id="default_user", limit=10)
        if not matches:
            return f"[INFO] No memory records found matching '{query}'. Nothing was deleted."

        deleted_summaries = []
        for record in matches:
            record_id = record.get("id")
            content = record.get("value", {})
            if record_id:
                memory_manager.client.table("langgraph_memory").delete().eq("id", record_id).execute()
                deleted_summaries.append(str(content)[:60])

        return f"[SUCCESS] Removed {len(deleted_summaries)} memory record(s) matching '{query}':\n" + "\n".join(
            f"  – {s}" for s in deleted_summaries
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
    try:
        emails = await email_service.fetch_unread_emails(max_results=limit)
        if not emails:
            return "[OUTBOX] No recent emails found in the outbox."

        lines = [f"[OUTBOX] Last {len(emails)} sent email(s):"]
        for i, email in enumerate(emails, 1):
            lines.append(
                f"  {i}. To: {email.get('sender')} | Subject: {email.get('subject')} | "
                f"Thread: {email.get('thread_id', 'N/A')}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in get_sent_emails: {e}")
        return f"[ERROR] Failed to retrieve email log: {e}"
