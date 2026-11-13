"""One operator-requested follow-up per outreach conversation; never scheduled sends."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core.store import store, ConflictError
from services.contacts import EligibilityError
from services.lead_service import ensure_qualified
from services.proposals import portfolio, CONTACT_EMAIL, CONTACT_PHONE, single_line
from services.report_service import instant

WAIT_DAYS = 7
SYNC_MINUTES = 15


def message_order(message):
    sent = instant(message.get("created_at"))
    return (sent.timestamp() if sent else float("-inf"), message["id"])


def approval_key(mailbox, thread_id):
    return (
        "followup_" + hashlib.sha256(f"{mailbox}:{thread_id}".encode()).hexdigest()[:24]
    )


def source_fingerprint(message):
    keys = (
        "id",
        "from",
        "to",
        "thread_id",
        "rfc_message_id",
        "subject",
        "body",
        "created_at",
        "approval_id",
        "provider_message_id",
    )
    return hashlib.sha256(
        json.dumps({k: message.get(k) for k in keys}, sort_keys=True).encode()
    ).hexdigest()


def context(outbound_id, mailbox, *, at=None, queued_id=None):
    at = at or datetime.now(timezone.utc)
    message = store.get("messages", outbound_id)
    if not message or not mailbox or message.get("from") != mailbox:
        raise KeyError(outbound_id)
    if (
        message.get("status") != "sent"
        or message.get("purpose") != "outreach"
        or message.get("followup_of")
        or not message.get("provider_message_id")
    ):
        raise EligibilityError(
            "Select a provider-confirmed initial outreach message; connection tests are excluded"
        )
    if not message.get("thread_id") or not message.get("rfc_message_id"):
        raise EligibilityError("Original Gmail thread or Message-ID is missing")
    if not message.get("subject") or any(
        "\r" in message.get(k, "") or "\n" in message.get(k, "")
        for k in ("subject", "rfc_message_id")
    ):
        raise EligibilityError("Original message headers are missing or invalid")
    sent = instant(message.get("created_at"))
    if not sent or at < sent + timedelta(days=WAIT_DAYS):
        raise EligibilityError(
            f"Follow-up becomes available {WAIT_DAYS} days after the initial outreach"
        )
    cursor = store.get("gmail_cursor", mailbox) or {}
    synced = instant(cursor.get("updated_at"))
    if (
        not synced
        or synced > at
        or at - synced > timedelta(minutes=SYNC_MINUTES)
        or synced < sent
        or message["thread_id"] not in cursor.get("thread_ids", [])
    ):
        raise EligibilityError(
            f"Sync Gmail replies within the last {SYNC_MINUTES} minutes before preparing or sending a follow-up"
        )
    thread = message["thread_id"]
    sent_in_thread = [
        m
        for m in store.list("messages")
        if m.get("from") == mailbox
        and m.get("thread_id") == thread
        and m.get("status") == "sent"
        and m.get("purpose") == "outreach"
    ]
    first = min(sent_in_thread, key=message_order)
    if first["id"] != outbound_id:
        raise EligibilityError(
            "Only the initial message in a conversation can have a follow-up"
        )
    if any(
        m.get("mailbox") == mailbox and m.get("thread_id") == thread
        for m in store.list("inbox")
    ):
        raise EligibilityError(
            "A reply, automated notice or bounce is recorded; review the conversation instead"
        )
    if any(
        e.get("mailbox") == mailbox
        and e.get("thread_id") == thread
        and e.get("outcome") != "unclassified"
        for e in store.list("outcomes")
    ):
        raise EligibilityError(
            "This conversation has an explicit outcome; no no-response follow-up is available"
        )
    active = store.get("approvals", queued_id or "") or {}
    own_dispatch = (
        active.get("dispatch_id") if active.get("status") == "sending" else None
    )
    if any(
        m.get("from") == mailbox
        and m.get("thread_id") == thread
        and m.get("status") in ("sending", "delivery_unknown")
        and not (m["id"] == own_dispatch and m.get("status") == "sending")
        for m in store.list("messages")
    ):
        raise EligibilityError(
            "A submission is in progress or uncertain; reconcile it before any follow-up"
        )
    key = approval_key(mailbox, thread)
    existing = store.get("approvals", key)
    if existing and existing["id"] != queued_id:
        raise EligibilityError(
            f"Follow-up already exists ({existing['status']}); review it in Approvals or history"
        )
    for draft in store.list("approvals"):
        if draft["id"] == queued_id:
            continue
        if (
            draft.get("sender_mailbox") == mailbox
            and draft.get("provider_thread_id") == thread
            and draft.get("status") not in ("sent", "rejected")
        ):
            raise EligibilityError(
                "Another draft is active for this conversation; review it first"
            )
    if any(
        m.get("from") == mailbox
        and m.get("thread_id") == thread
        and m.get("followup_of")
        and m.get("status") == "sent"
        for m in store.list("messages")
    ):
        raise EligibilityError("The single permitted follow-up was already sent")
    if any(
        m.get("from") == mailbox
        and m.get("thread_id") == thread
        and m.get("status") == "sent"
        and m["id"] != outbound_id
        for m in store.list("messages")
    ):
        raise EligibilityError(
            "Another message was already sent in this conversation; review its history instead"
        )
    initial_approval = store.get("approvals", message.get("approval_id") or "") or {}
    lead_id = initial_approval.get("lead_id") or (
        initial_approval.get("lead_data") or {}
    ).get("id")
    if not lead_id:
        raise EligibilityError(
            "Initial outreach has no linked reviewed lead; follow-up is unavailable"
        )
    lead = ensure_qualified(lead_id, message["to"])
    return message, lead


def list_candidates(mailbox):
    rows, seen = [], set()
    messages = sorted(store.list("messages"), key=message_order)
    for message in messages:
        if (
            message.get("from") != mailbox
            or message.get("purpose") != "outreach"
            or message.get("status") != "sent"
            or message.get("followup_of")
        ):
            continue
        thread = message.get("thread_id") or message["id"]
        if thread in seen:
            continue
        seen.add(thread)
        blocker = ""
        try:
            context(message["id"], mailbox)
        except (ValueError, KeyError) as exc:
            blocker = str(exc)
        sent = instant(message.get("created_at"))
        rows.append(
            {
                "id": message["id"],
                "recipient": message.get("to", ""),
                "subject": message.get("subject", ""),
                "sent_at": message.get("created_at"),
                "due_at": (
                    (sent + timedelta(days=WAIT_DAYS)).isoformat() if sent else None
                ),
                "eligible": not blocker,
                "blocker": blocker,
            }
        )
    return {
        "wait_days": WAIT_DAYS,
        "max_followups": 1,
        "sync_minutes": SYNC_MINUTES,
        "candidates": rows,
        "automatic_sending": False,
    }


def preview(outbound_id, mailbox):
    message, lead = context(outbound_id, mailbox)
    catalog = portfolio()
    name = single_line(lead["review"].get("confirmed_name") or lead["name"])
    subject = (
        message["subject"]
        if message["subject"].casefold().startswith("re:")
        else "Re: " + message["subject"]
    )
    body = (
        f"Hi {name} team,\n\nI'm following up on my earlier email about a website for your business. "
        "Would a conversation about your requirements be useful? We can discuss scope before preparing a quotation.\n\n"
        f"Our portfolio: {catalog['portfolio_url']}\n\n"
        "If the timing isn't right, no action is needed.\n\n"
        f"Best,\n{catalog['agency_name']}\n{CONTACT_EMAIL} | {CONTACT_PHONE}\n\n"
        "If you'd prefer no further outreach, reply 'unsubscribe'."
    )
    return store.put(
        "followup_previews",
        uuid4().hex,
        {
            "outbound_id": outbound_id,
            "sender_mailbox": mailbox,
            "source_fingerprint": source_fingerprint(message),
            "lead_id": lead["id"],
            "lead_revision": lead["revision"],
            "portfolio_version": catalog["version"],
            "subject": subject,
            "body": body,
        },
    )


def queue(outbound_id, mailbox, preview_id, body):
    from agents.human_approval import queue_approval

    if not body.strip():
        raise ValueError("Provide a follow-up message")
    message, lead = context(outbound_id, mailbox)
    saved = store.get("followup_previews", preview_id)
    if (
        not saved
        or saved["outbound_id"] != outbound_id
        or saved["sender_mailbox"] != mailbox
    ):
        raise ValueError(
            "Follow-up preview does not belong to this message and mailbox"
        )
    if (
        saved["source_fingerprint"] != source_fingerprint(message)
        or saved["lead_id"] != lead["id"]
        or saved["lead_revision"] != lead["revision"]
        or saved["portfolio_version"] != portfolio()["version"]
    ):
        raise ConflictError(
            "Original message, lead or portfolio changed; generate a fresh follow-up"
        )
    return queue_approval(
        approval_key(mailbox, message["thread_id"]),
        {
            "recipient_email": message["to"],
            "sender_mailbox": mailbox,
            "subject": saved["subject"],
            "draft_response": body,
            "purpose": "outreach",
            "intent": "sales",
            "lead_id": lead["id"],
            "lead_revision": lead["revision"],
            "client_name": lead["name"],
            "provider_thread_id": message["thread_id"],
            "in_reply_to": message["rfc_message_id"],
            "followup_of": outbound_id,
            "followup_snapshot": {
                **saved,
                "edited_before_queue": body != saved["body"],
            },
        },
    )


def validate(approval, mailbox):
    if not approval.get("followup_of"):
        return
    try:
        message, lead = context(
            approval["followup_of"], mailbox, queued_id=approval["id"]
        )
    except (ValueError, KeyError) as exc:
        raise EligibilityError(str(exc)) from exc
    if (
        approval["recipient_email"] != message["to"]
        or approval.get("lead_id") != lead["id"]
        or (approval.get("followup_snapshot") or {}).get("source_fingerprint")
        != source_fingerprint(message)
    ):
        raise EligibilityError(
            "Follow-up source changed; review the original conversation"
        )
