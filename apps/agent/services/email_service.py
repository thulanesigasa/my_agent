"""Gmail adapter. Never substitutes sample mail or simulated success."""

import asyncio
import base64
import logging
from email.mime.text import MIMEText
from uuid import uuid4

from config import settings
from core.store import store

logger = logging.getLogger("agent.email_service")


class EmailUnavailable(RuntimeError):
    """No provider request was attempted; safe to retry after configuration."""


class DeliveryUnknown(RuntimeError):
    """Provider request may have succeeded. Reconcile before retrying."""


class GmailServiceAdapter:
    def __init__(self):
        self.client = None
        self.is_configured = all(
            (
                settings.GMAIL_CLIENT_ID,
                settings.GMAIL_CLIENT_SECRET,
                settings.GMAIL_REFRESH_TOKEN,
            )
        )
        if self.is_configured:
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build

                creds = Credentials(
                    token=None,
                    refresh_token=settings.GMAIL_REFRESH_TOKEN,
                    client_id=settings.GMAIL_CLIENT_ID,
                    client_secret=settings.GMAIL_CLIENT_SECRET,
                    token_uri="https://oauth2.googleapis.com/token",
                )
                self.client = build(
                    "gmail", "v1", credentials=creds, cache_discovery=False
                )
            except Exception:
                logger.exception("Gmail initialization failed; email is unavailable")

    async def fetch_unread_emails(self, max_results=5):
        if self.client is None:
            raise EmailUnavailable("Gmail is not configured or could not initialise")

        def fetch():
            result = (
                self.client.users()
                .messages()
                .list(userId="me", q="is:unread", maxResults=max_results)
                .execute()
            )
            emails = []
            for item in result.get("messages", []):
                msg = (
                    self.client.users()
                    .messages()
                    .get(userId="me", id=item["id"])
                    .execute()
                )
                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                emails.append(
                    {
                        "id": msg["id"],
                        "thread_id": msg.get("threadId"),
                        "sender": headers.get("from", ""),
                        "subject": headers.get("subject", ""),
                        "body": msg.get("snippet", ""),
                    }
                )
            return emails

        return await asyncio.to_thread(fetch)

    async def send_email(
        self, to, subject, body, thread_id=None, *, purpose="notification", company=""
    ):
        if self.client is None:
            raise EmailUnavailable("Gmail is not configured or could not initialise")
        if not to or "@" not in to or not body or not subject:
            raise ValueError("Recipient, subject and non-empty body are required")
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        payload = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")}
        if thread_id:
            payload["threadId"] = thread_id
        record_id = uuid4().hex
        record = {
            "to": to,
            "subject": subject,
            "body": body,
            "purpose": purpose,
            "company": company,
            "thread_id": thread_id,
            "status": "sending",
        }
        store.put("messages", record_id, record)
        try:
            sent = await asyncio.to_thread(
                lambda: self.client.users()
                .messages()
                .send(userId="me", body=payload)
                .execute()
            )
            if not sent.get("id"):
                raise DeliveryUnknown("Gmail returned no message ID")
            store.transition(
                "messages",
                record_id,
                ["sending"],
                "sent",
                provider_message_id=sent["id"],
                thread_id=sent.get("threadId"),
            )
        except Exception as exc:
            # Even a response-parsing or persistence failure after submission is uncertain.
            store.transition(
                "messages",
                record_id,
                ["sending"],
                "delivery_unknown",
                error="Gmail submission requires manual reconciliation",
            )
            raise DeliveryUnknown(
                "Send outcome is uncertain; inspect Gmail Sent before any retry"
            ) from exc
        return {
            "status": "sent",
            "id": sent["id"],
            "thread_id": sent.get("threadId"),
            "to": to,
            "subject": subject,
        }


email_service = GmailServiceAdapter()
