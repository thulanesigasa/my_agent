"""
Notification Service: Priority alerts for human-in-the-loop actions and web push notifications.
"""
import logging
from typing import Dict, Any, Optional
from services.email_service import email_service

logger = logging.getLogger("agent.notification_service")

ADMIN_EMAIL = "pharezsigasa@gmail.com"
DASHBOARD_APPROVAL_URL = "https://ts-industries.co.za/dashboard/approvals"


async def notify_admin_approval_needed(
    thread_id: str,
    client_name: str,
    intent: str = "quote_request",
    details: str = ""
) -> Dict[str, Any]:
    """
    Sends a priority email notification to the admin (Pharez) containing a direct link
    to the dashboard approval queue when an action hits the human_approval_node.
    """
    approval_link = f"{DASHBOARD_APPROVAL_URL}/{thread_id}"
    subject = f"⚠️ ACTION REQUIRED: Human Approval Needed for {client_name}"

    body = (
        f"Hello Pharez,\n\n"
        f"An action by T.S Industries AI Agent requires your review and approval before dispatch.\n\n"
        f"• Client/Prospect: {client_name}\n"
        f"• Intent: {intent}\n"
        f"• Thread ID: {thread_id}\n"
        f"{f'• Details: {details}' if details else ''}\n\n"
        f"Direct Approval Link:\n{approval_link}\n\n"
        f"Best regards,\nT.S Industries Autonomous Agent System"
    )

    logger.info(f"Sending human approval notification email to {ADMIN_EMAIL} for thread {thread_id}...")

    # Send Priority Email
    email_result = await email_service.send_email(
        to=ADMIN_EMAIL,
        subject=subject,
        body=body,
        thread_id=thread_id
    )

    # Trigger Web Push Notification
    push_result = await send_web_push(
        thread_id=thread_id,
        title=f"Approval Needed: {client_name}",
        body=f"Intent: '{intent}'. Tap to approve in Dashboard."
    )

    return {
        "status": "notification_sent",
        "email_result": email_result,
        "push_result": push_result,
        "approval_link": approval_link
    }


async def send_web_push(thread_id: str, title: str, body: str) -> Dict[str, Any]:
    """
    Web Push Notification placeholder. Wired to Next.js frontend via VAPID keys, Pusher, or Firebase.
    """
    logger.info(f"[WebPush] Triggering push notification for thread {thread_id}: '{title}'")
    return {
        "status": "push_dispatched",
        "thread_id": thread_id,
        "title": title,
        "body": body,
        "link": f"{DASHBOARD_APPROVAL_URL}/{thread_id}"
    }
