"""Durable approval queue. Dispatch uses exactly the reviewed persisted draft."""

from email.utils import parseaddr
from uuid import uuid4

from core.store import store
from services.contacts import ensure_eligible, EligibilityError
from services.email_service import email_service, EmailUnavailable, DeliveryUnknown


def queue_approval(approval_id, item):
    email = item.get("email_input") or {}
    recipient = parseaddr(item.get("recipient_email") or email.get("sender", ""))[1]
    subject = item.get("subject") or email.get("subject", "")
    body = item.get("draft_response", "")
    if (
        not recipient
        or "@" not in recipient
        or not subject
        or not body
        or not body.strip()
    ):
        raise ValueError("Approval requires a recipient, subject and non-empty draft")
    return store.queue_approval(
        approval_id,
        {
            **item,
            "recipient_email": recipient,
            "subject": subject,
            "sender_mailbox": item.get("sender_mailbox")
            or email_service.expected_email,
        },
    )


async def human_approval_node(state):
    email = state.get("email_input") or {}
    approval_id = "reply_" + str(email.get("id") or uuid4().hex)
    subject = email.get("subject") or "Inquiry"
    item = queue_approval(
        approval_id,
        {
            "intent": state.get("intent", "client_inquiry"),
            "email_input": email,
            "provider_thread_id": email.get("thread_id"),
            "subject": (
                subject if subject.lower().startswith("re:") else f"Re: {subject}"
            ),
            "draft_response": state.get("draft_response", ""),
            "purpose": email.get("conversation_purpose", "reply"),
            "in_reply_to": email.get("rfc_message_id"),
            "references": email.get("references"),
        },
    )
    return {
        **state,
        "sender": "human_approval",
        "approval_status": item["status"],
        "needs_human_approval": True,
        "final_output": "Draft saved in the Approval Queue for review.",
    }


async def approve_draft(thread_id):
    item = store.get("approvals", thread_id)
    if item is None:
        raise KeyError(thread_id)
    if item["status"] == "sent":
        return {"status": "sent", "item": item, "already_sent": True}
    if (
        item.get("sender_mailbox")
        and item["sender_mailbox"] != email_service.expected_email
    ):
        raise EligibilityError("This draft belongs to another sending mailbox")
    ensure_eligible(item["recipient_email"], item.get("purpose", "outreach"))
    from services.reply_service import validate_queued_reply

    validate_queued_reply(item, email_service.expected_email)
    from services.followups import validate as validate_followup

    validate_followup(item, email_service.expected_email)
    lead_id = item.get("lead_id") or (item.get("lead_data") or {}).get("id")
    if item.get("purpose") == "outreach" and lead_id:
        from services.lead_service import ensure_qualified

        ensure_qualified(lead_id, item["recipient_email"])
    attachment = None
    if item.get("purpose") == "report":
        from services.report_service import report_attachment

        attachment = report_attachment(
            item.get("report_id"), email_service.expected_email
        )
    # Claim atomically before network I/O. Concurrent requests and interrupted sends cannot resend.
    item = store.transition(
        "approvals", thread_id, ["pending", "edited", "failed"], "sending", error=None
    )
    try:
        result = await email_service.send_email(
            to=item["recipient_email"],
            subject=item["subject"],
            body=item["draft_response"],
            thread_id=item.get("provider_thread_id"),
            purpose=item.get("purpose", "outreach"),
            approval_id=thread_id,
            in_reply_to=item.get("in_reply_to"),
            references=item.get("references"),
            attachment=attachment,
            company=item.get("client_name")
            or item.get("lead_data", {}).get("name", ""),
        )
        if result.get("status") != "sent" or not result.get("id"):
            raise DeliveryUnknown("Provider did not confirm the send")
    except (EmailUnavailable, EligibilityError) as exc:
        store.transition(
            "approvals",
            thread_id,
            ["sending"],
            "failed",
            error=(
                str(exc)
                if isinstance(exc, EligibilityError)
                else "Gmail unavailable; configure it before retrying"
            ),
        )
        raise
    except Exception:
        store.transition(
            "approvals",
            thread_id,
            ["sending"],
            "delivery_unknown",
            error="Delivery is uncertain. Check Gmail Sent; automatic resend is blocked.",
        )
        raise
    item = store.get("approvals", thread_id)
    if item["status"] != "sent":
        item = store.transition(
            "approvals",
            thread_id,
            ["sending"],
            "sent",
            provider_message_id=result["id"],
            provider_thread_id=result.get("thread_id"),
        )
    return {"status": "sent", "item": item}


async def reject_or_edit_draft(thread_id, new_content=None):
    if new_content is not None:
        if not new_content.strip():
            raise ValueError("Edited draft cannot be empty")
        item = store.transition(
            "approvals",
            thread_id,
            ["pending", "edited", "failed"],
            "edited",
            draft_response=new_content,
        )
        return {"status": "edited", "item": item}
    item = store.transition(
        "approvals", thread_id, ["pending", "edited", "failed"], "rejected"
    )
    return {"status": "rejected", "item": item}


def get_pending_approvals():
    return [
        item
        for item in store.list("approvals")
        if item["status"] not in ("sent", "rejected")
    ]
