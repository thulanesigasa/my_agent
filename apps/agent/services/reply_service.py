"""Conservative local reply suggestions. Incoming text never executes agent commands."""

import hashlib
import json
import re
from uuid import uuid4

from core.store import store, ConflictError
from services.contacts import ensure_eligible, EligibilityError
from services.mail_parser import new_text
from services.proposals import portfolio, CONTACT_EMAIL, CONTACT_PHONE
from services.report_service import incoming_time


def fingerprint(mail):
    fields = (
        "mailbox",
        "sender",
        "subject",
        "body",
        "thread_id",
        "rfc_message_id",
        "references",
        "provider_timestamp",
        "matched_outbound_id",
        "automated",
        "bounce",
        "unsubscribe",
    )
    return hashlib.sha256(
        json.dumps({key: mail.get(key) for key in fields}, sort_keys=True).encode()
    ).hexdigest()


def assess_reply(mail):
    """Suggestions only: do not change consent, confirmed outcomes or send anything."""
    text = new_text(mail.get("body") or "")[:20000].replace("’", "'").casefold()
    evidence = []
    category, reason = (
        "needs_review",
        "No clear supported signal; review the message in context",
    )
    if mail.get("bounce"):
        category, reason = "bounced", "Gmail parser recorded a delivery notification"
    elif mail.get("automated"):
        category, reason = "automated", "Gmail parser marked this message as automated"
    elif mail.get("unsubscribe"):
        category, reason = (
            "unsubscribed",
            "Existing opt-out detection applies; do not contact",
        )
    else:
        negative = re.search(
            r"\b(not interested|no thanks|no thank you|not looking for|don't need|do not need|already have a website)\b",
            text,
        )
        positive = re.search(
            r"\b(i am interested|i'm interested|we are interested|we're interested|please send (?:me |us )?(?:more information|more details|a quote|a quotation)|let's discuss|let us discuss)\b",
            text,
        )
        uncertain = re.search(r"\b(not sure|unsure|maybe|might|if|but|however)\b", text)
        question = re.search(
            r"\b(how much|what (?:is|are)|can you|could you|do you|tell me|tell us|pricing|price|cost|quote|quotation)\b",
            text,
        )
        for match in (negative, positive, uncertain, question):
            if match:
                evidence.append(match.group(0))
        if uncertain or (negative and positive):
            reason = "Mixed or conditional wording; review before interpreting intent"
        elif negative:
            category, reason = (
                "declined",
                "Explicit negative wording; no response template offered",
            )
        elif positive:
            category, reason = (
                "interested",
                "Explicit interest or request for further details",
            )
        elif "?" in text or question:
            category, reason = (
                "question",
                "A question or request needs an operator answer",
            )
    return {
        "category": category,
        "reason": reason,
        "evidence": evidence,
        "suggested_outcome": (
            category if category in ("interested", "declined") else None
        ),
        "template_available": category in ("interested", "question"),
        "version": 1,
        "fingerprint": fingerprint(mail),
    }


def reply_context(record_id, mailbox, *, current=True):
    mail = store.get("inbox", record_id)
    if not mail or not mailbox or mail.get("mailbox") != mailbox:
        raise KeyError(record_id)
    originals = [
        m
        for m in store.list("messages")
        if m.get("from") == mailbox
        and m.get("to") == mail.get("sender")
        and m.get("thread_id") == mail.get("thread_id")
        and m.get("status") == "sent"
        and m.get("purpose") in ("outreach", "test")
    ]
    if not originals or not mail.get("thread_id"):
        raise EligibilityError("Reply is not linked to a tracked conversation")
    if mail.get("automated") or mail.get("bounce") or mail.get("unsubscribe"):
        raise EligibilityError(
            "Do not reply to automated messages, bounces or opt-outs"
        )
    if current:
        human = [
            m
            for m in store.list("inbox")
            if m.get("mailbox") == mailbox
            and m.get("thread_id") == mail["thread_id"]
            and m.get("sender") == mail["sender"]
            and not m.get("automated")
            and not m.get("bounce")
        ]
        latest = max(
            human,
            key=lambda m: (
                (incoming_time(m).timestamp() if incoming_time(m) else float("-inf")),
                m["id"],
            ),
        )
        if latest["id"] != record_id:
            raise ConflictError("A newer human reply exists; review that message first")
    original = next(
        (m for m in originals if m["id"] == mail.get("matched_outbound_id")),
        originals[0],
    )
    return mail, original


def reply_preview(record_id, mailbox):
    mail, original = reply_context(record_id, mailbox)
    purpose = "test" if original["purpose"] == "test" else "reply"
    ensure_eligible(mail["sender"], purpose)
    assessment = assess_reply(mail)
    if not assessment["template_available"]:
        raise EligibilityError(
            "This reply needs manual review; no response template is available"
        )
    if not mail.get("rfc_message_id"):
        raise EligibilityError(
            "Incoming Message-ID is missing; a threaded reply cannot be prepared"
        )
    catalog = portfolio()
    opening = (
        "Thank you for your interest."
        if assessment["category"] == "interested"
        else "Thank you for your question."
    )
    body = (
        f"Hello,\n\n{opening} To help us understand the scope, could you share the services you want to present, the pages or features you need, and your preferred timeline?\n\n"
        "We can prepare a quotation once we understand your requirements.\n\n"
        f"Our portfolio: {catalog['portfolio_url']}\n\n"
        f"Best,\n{catalog['agency_name']}\n{CONTACT_EMAIL} | {CONTACT_PHONE}\n\n"
        "If you'd prefer no further outreach, reply 'unsubscribe'."
    )
    subject = mail.get("subject") or "Website enquiry"
    subject = subject if subject.casefold().startswith("re:") else f"Re: {subject}"
    return store.put(
        "reply_previews",
        uuid4().hex,
        {
            "incoming_id": record_id,
            "sender_mailbox": mailbox,
            "fingerprint": fingerprint(mail),
            "portfolio_version": catalog["version"],
            "assessment": assessment,
            "subject": subject,
            "body": body,
        },
    )


def queue_reply(record_id, body, mailbox, preview_id=None):
    from agents.human_approval import queue_approval

    if not body.strip():
        raise ValueError("Provide a reply message")
    mail, original = reply_context(record_id, mailbox)
    purpose = "test" if original["purpose"] == "test" else "reply"
    ensure_eligible(mail["sender"], purpose)
    if not mail.get("rfc_message_id"):
        raise EligibilityError(
            "Incoming Message-ID is missing; a threaded reply cannot be prepared"
        )
    snapshot = None
    if preview_id:
        snapshot = store.get("reply_previews", preview_id)
        if (
            not snapshot
            or snapshot["incoming_id"] != record_id
            or snapshot["sender_mailbox"] != mailbox
        ):
            raise ValueError(
                "Reply preview does not belong to this message and mailbox"
            )
        if (
            snapshot["fingerprint"] != fingerprint(mail)
            or snapshot["portfolio_version"] != portfolio()["version"]
        ):
            raise ConflictError("Reply or portfolio changed; generate a fresh response")
        snapshot = {**snapshot, "edited_before_queue": body != snapshot["body"]}
    subject = mail.get("subject") or "Website enquiry"
    return queue_approval(
        "reply_" + record_id,
        {
            "recipient_email": mail["sender"],
            "subject": (
                subject if subject.casefold().startswith("re:") else f"Re: {subject}"
            ),
            "sender_mailbox": mailbox,
            "draft_response": body,
            "purpose": purpose,
            "intent": "client_inquiry",
            "provider_thread_id": mail["thread_id"],
            "in_reply_to": mail["rfc_message_id"],
            "references": mail.get("references"),
            "incoming_id": record_id,
            "incoming_fingerprint": fingerprint(mail),
            **({"reply_snapshot": snapshot} if snapshot else {}),
        },
    )


def validate_queued_reply(approval, mailbox):
    """Called at approval and again immediately before the Gmail submission."""
    if not approval.get("incoming_id"):
        return  # Legacy approvals retain their existing contact checks.
    try:
        mail, _ = reply_context(approval["incoming_id"], mailbox)
    except (ValueError, KeyError) as exc:
        raise EligibilityError(str(exc)) from exc
    if (
        approval.get("incoming_fingerprint") != fingerprint(mail)
        or approval["recipient_email"] != mail["sender"]
    ):
        raise EligibilityError(
            "Incoming reply changed; reject this draft and review the conversation"
        )


def confirm_outcome(record_id, mailbox, expected_fingerprint, outcome, note):
    mail, original = reply_context(record_id, mailbox)
    if fingerprint(mail) != expected_fingerprint:
        raise ConflictError("Reply changed; reload before confirming an outcome")
    if outcome not in ("interested", "declined", "unclassified") or not note.strip():
        raise ValueError("Choose a supported outcome and record your evidence")
    return store.record_outcome(
        mailbox,
        original["thread_id"],
        mail["sender"],
        outcome,
        f"Reply {record_id}: {note.strip()}",
    )
