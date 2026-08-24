"""
Human Approval Agent Node & Helper Functions for Human-in-the-Loop workflows.
Triggers priority notifications to admin via notification_service and updates CRM status.
"""
import logging
from typing import Dict, Any, Optional, List
from core.state import AgentState
from services.email_service import email_service
from services.whatsapp_service import whatsapp_service
from services.notification_service import notify_admin_approval_needed
from services.crm_service import update_project_status, upsert_client
from core.memory import memory_manager

logger = logging.getLogger("agent.node.human_approval")

# In-memory approval queue (persisted via Supabase/MemorySaver in production)
PENDING_APPROVAL_QUEUE: Dict[str, Dict[str, Any]] = {
    "a1": {
        "thread_id": "a1",
        "client_name": "Mike's Auto Repair",
        "recipient_email": "mike@mikesauto.com",
        "subject": "Web Presence Proposal",
        "intent": "quote_request",
        "draft_response": "Hi Mike's Auto Repair,\n\nWe help local businesses get online fast. Claim your free 30-min strategy call.\n\nBest,\nAgent Team",
        "status": "pending",
        "created_at": "Just now"
    },
    "a2": {
        "thread_id": "a2",
        "client_name": "Sunrise Bakery",
        "recipient_email": "hello@sunrisebakery.biz",
        "subject": "Grow Your Bakery Online",
        "intent": "sales",
        "draft_response": "Hi Sunrise Bakery,\n\nA professional website could bring dozens of new customers weekly.\n\nBest,\nAgent Team",
        "status": "pending",
        "created_at": "Just now"
    }
}


async def human_approval_node(state: AgentState) -> AgentState:
    """
    LangGraph Approval Node:
    Pauses or intercepts execution for high-risk client inquiries or external dispatches.
    Sends priority notification email & push alert to admin.
    Automatically updates CRM project pipeline when approved.
    """
    logger.info("Executing Human Approval Node...")
    approval_status = state.get("approval_status")
    intent = state.get("intent", "general")
    draft = state.get("draft_response", "")
    email_input = state.get("email_input") or {}

    thread_id = email_input.get("thread_id") or "session_001"
    client_name = email_input.get("sender") or email_input.get("company") or "Prospect/Client"
    recipient_email = email_input.get("sender", "client@enterprise.com")

    # If action has been approved by human
    if approval_status == "approved":
        logger.info(f"Human Approval Granted for thread '{thread_id}'. Executing action...")
        if intent in ("sales", "client_inquiry", "quote_request"):
            subject = f"Re: {email_input.get('subject', 'Inquiry Response')}"
            await email_service.send_email(to=recipient_email, subject=subject, body=draft, thread_id=thread_id)

            # Update CRM sales pipeline to 'Quoted' or 'In Progress'
            crm_status = "Quoted" if intent == "quote_request" else "In Progress"
            await update_project_status(
                client_email=recipient_email,
                status=crm_status,
                scope_summary=draft[:150]
            )

            state["final_output"] = f"[SUCCESS] Approved & Sent Email to {recipient_email}. Updated CRM status to '{crm_status}'."

        state["needs_human_approval"] = False
        if thread_id in PENDING_APPROVAL_QUEUE:
            del PENDING_APPROVAL_QUEUE[thread_id]
        return state

    # If action was edited or rejected
    if approval_status == "rejected":
        logger.info(f"Action rejected by human for thread '{thread_id}'.")
        state["final_output"] = "[ERROR] Action rejected by human review."
        state["needs_human_approval"] = False
        if thread_id in PENDING_APPROVAL_QUEUE:
            del PENDING_APPROVAL_QUEUE[thread_id]
        return state

    # Otherwise flag as pending approval in queue
    state["approval_status"] = "pending"
    state["sender"] = "human_approval"
    pending_item = {
        "thread_id": thread_id,
        "intent": intent,
        "email_input": email_input,
        "draft_response": draft,
        "status": "pending",
        "created_at": "Just now"
    }
    PENDING_APPROVAL_QUEUE[thread_id] = pending_item

    # Upsert client in CRM as Lead
    await upsert_client(name=client_name, email=recipient_email)
    await update_project_status(client_email=recipient_email, status="Lead")

    # Send priority alert to Admin (Pharez) with direct approval link
    try:
        await notify_admin_approval_needed(
            thread_id=thread_id,
            client_name=client_name,
            intent=intent,
            details=draft[:120]
        )
    except Exception as e:
        logger.error(f"Error sending approval notification: {e}")

    # Persist pending item in Supabase for audit trail
    await memory_manager.save_memory(
        f"Pending Human Approval [{intent}]: {draft[:80]}...",
        metadata={"type": "approval_pending", "thread_id": thread_id}
    )

    return state


async def approve_draft(thread_id: str) -> Dict[str, Any]:
    """
    Helper function to approve pending action and resume workflow.
    """
    if thread_id in PENDING_APPROVAL_QUEUE:
        item = PENDING_APPROVAL_QUEUE[thread_id]
        item["status"] = "approved"
        return {"status": "approved", "item": item}
    return {"status": "not_found", "thread_id": thread_id}


async def reject_or_edit_draft(thread_id: str, new_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Helper function to edit or reject a pending draft.
    """
    if thread_id in PENDING_APPROVAL_QUEUE:
        item = PENDING_APPROVAL_QUEUE[thread_id]
        if new_content:
            item["draft_response"] = new_content
            item["status"] = "edited"
            return {"status": "edited", "new_content": new_content}
        else:
            item["status"] = "rejected"
            return {"status": "rejected"}
    return {"status": "not_found", "thread_id": thread_id}


def get_pending_approvals() -> List[Dict[str, Any]]:
    """
    Returns list of all active pending actions requiring human review.
    """
    return list(PENDING_APPROVAL_QUEUE.values())
