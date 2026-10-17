"""Private operator controls for Gmail tests, contacts, sync and reconciliation."""

from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from config import settings
from core.store import store, ConflictError
from core.security import verify_api_key
from services.contacts import (
    save_contact,
    ensure_eligible,
    EligibilityError,
    normalize_email,
)
from services.email_service import email_service, EmailUnavailable, DeliveryUnknown
from services.inbox_service import process_inbox_batch, process_pending
from agents.human_approval import queue_approval

router = APIRouter(
    prefix="/api/gmail", tags=["Gmail"], dependencies=[Depends(verify_api_key)]
)


async def operation(call):
    try:
        return await call()
    except KeyError:
        raise HTTPException(status_code=404, detail="Record not found")
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except EligibilityError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except EmailUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except DeliveryUnknown as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Gmail operation failed; check connection and server configuration",
        )


@router.get("/status")
async def connection_status():
    return {
        "configured": email_service.is_configured,
        "connection": store.get("gmail_connection", "current"),
        "reply_drafting_enabled": settings.GMAIL_DRAFT_REPLIES,
        "cursor": store.get("gmail_cursor", email_service.expected_email or ""),
        "setup_command": "python connect_gmail.py authorize --account YOUR_GMAIL_ADDRESS",
    }


@router.post("/verify")
async def verify_connection():
    profile = await operation(email_service.get_profile)
    return {"status": "verified", "email": profile["emailAddress"]}


@router.post("/sync")
async def sync_mailbox():
    return await operation(process_inbox_batch)


@router.get("/inbox")
async def incoming_messages():
    return {
        "messages": [
            mail
            for mail in store.list("inbox")
            if mail.get("mailbox") == email_service.expected_email
        ]
    }


@router.post("/inbox/{record_id}/retry")
async def retry_incoming(record_id: str):
    async def retry():
        mail = store.get("inbox", record_id)
        if not mail or mail.get("mailbox") != email_service.expected_email:
            raise KeyError(record_id)
        store.transition("inbox", record_id, ["failed"], "pending", error=None)
        return await process_pending()

    return await operation(retry)


class ContactInput(BaseModel):
    name: str = Field(default="", max_length=200)
    verified: bool = False
    consent: Literal["unknown", "granted", "declined", "unsubscribed"] = "unknown"
    evidence: str = Field(default="", max_length=2000)
    test_recipient: bool = False


@router.get("/contacts")
async def contacts():
    return {"contacts": store.list("contacts")}


@router.put("/contacts/{email}")
async def update_contact(email: str, payload: ContactInput):
    async def save():
        return save_contact(email, **payload.model_dump())

    return await operation(save)


class DraftInput(BaseModel):
    recipient: str = ""
    subject: str = Field(default="", max_length=300)
    body: str = Field(min_length=1, max_length=20000)
    purpose: Literal["test", "outreach", "reply"] = "test"
    incoming_id: str | None = None
    lead_id: str | None = None


@router.post("/drafts")
async def create_draft(payload: DraftInput):
    async def create():
        if payload.purpose == "outreach":
            from services.lead_service import draft_lead, ensure_qualified

            if not payload.lead_id:
                raise EligibilityError(
                    "Review a candidate and create its outreach draft in Leads"
                )
            ensure_qualified(payload.lead_id, payload.recipient)
            return draft_lead(
                payload.lead_id,
                payload.subject,
                payload.body,
                email_service.expected_email,
            )
        data = {
            "recipient_email": (
                normalize_email(payload.recipient) if payload.purpose != "reply" else ""
            ),
            "subject": payload.subject,
            "draft_response": payload.body,
            "purpose": payload.purpose,
            "intent": "sales",
        }
        if payload.purpose == "reply":
            incoming = store.get("inbox", payload.incoming_id or "")
            if not incoming or incoming.get("mailbox") != email_service.expected_email:
                raise ValueError(
                    "Select a recorded incoming message from the connected mailbox"
                )
            if incoming.get("automated") or incoming.get("unsubscribe"):
                raise EligibilityError(
                    "Do not reply to automated messages or opt-out requests"
                )
            subject = incoming["subject"]
            data.update(
                recipient_email=incoming["sender"],
                subject=(
                    subject if subject.lower().startswith("re:") else f"Re: {subject}"
                ),
                provider_thread_id=incoming["thread_id"],
                in_reply_to=incoming["rfc_message_id"],
                references=incoming.get("references"),
                purpose=incoming.get("conversation_purpose", "reply"),
            )
        elif not payload.subject.strip():
            raise ValueError("Subject is required")
        if (
            data["purpose"] == "test"
            and data["recipient_email"] == email_service.expected_email
        ):
            raise ValueError(
                "Use a different mailbox you control to verify the reply cycle"
            )
        ensure_eligible(data["recipient_email"], data["purpose"])
        return queue_approval("manual_" + uuid4().hex, data)

    return await operation(create)


@router.post("/approvals/{approval_id}/reconcile")
async def reconcile_submission(approval_id: str):
    return await operation(lambda: email_service.reconcile(approval_id))
