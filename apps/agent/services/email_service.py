"""Gmail OAuth, bounded reads, correlated dispatch and targeted mailbox history."""

import asyncio
import base64
import logging
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.policy import SMTP
from email.utils import formatdate
from uuid import uuid4

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from auth.gmail_credentials import load_credentials
from config import settings
from core.store import store
from services.mail_parser import parse_message
from services.contacts import ensure_eligible, EligibilityError

logger = logging.getLogger("agent.email_service")


class EmailUnavailable(RuntimeError):
    """No accepted send; configuration/authentication must be corrected."""


class DeliveryUnknown(RuntimeError):
    """Submission may have succeeded. Reconcile before retrying."""


class GmailServiceAdapter:
    def __init__(self):
        self.client = None
        self.expected_email = None
        self.is_configured = False
        self._lock = threading.RLock()
        self._configure()

    def _configure(self):
        try:
            credentials, self.expected_email = load_credentials(settings)
            self.is_configured = credentials is not None
            if credentials:
                import httplib2
                import google_auth_httplib2
                from googleapiclient.discovery import build

                http = google_auth_httplib2.AuthorizedHttp(
                    credentials, http=httplib2.Http(timeout=20)
                )
                self.client = build("gmail", "v1", http=http, cache_discovery=False)
        except Exception:
            self.is_configured = False
            logger.warning(
                "Gmail credentials could not be loaded. Run connect_gmail.py locally."
            )

    async def _read(self, factory):
        if self.client is None:
            self._configure()
        if self.client is None:
            raise EmailUnavailable(
                "Gmail is not configured. Run connect_gmail.py authorize locally"
            )

        def execute():
            with self._lock:
                for attempt in range(3):
                    try:
                        return factory().execute(num_retries=0)
                    except HttpError as exc:
                        if (
                            exc.resp.status not in (429, 500, 502, 503, 504)
                            or attempt == 2
                        ):
                            raise
                        time.sleep(0.5 * (2**attempt))

        try:
            return await asyncio.to_thread(execute)
        except RefreshError as exc:
            self._connection_state("reauthorization_required")
            raise EmailUnavailable(
                "Gmail authorisation expired or was revoked. Run connect_gmail.py authorize again"
            ) from exc
        except HttpError as exc:
            if exc.resp.status in (401, 403):
                self._connection_state("authorization_error")
                raise EmailUnavailable(
                    "Gmail access was refused. Check API enablement, account policy and granted permissions"
                ) from exc
            if exc.resp.status != 404:
                self._connection_state("read_error")
                raise EmailUnavailable(
                    "Gmail read failed or was rate limited; sync can be retried"
                ) from exc
            raise

    def _connection_state(self, status, **values):
        store.put("gmail_connection", "current", {"status": status, **values})

    async def get_profile(self):
        profile = await self._read(lambda: self.client.users().getProfile(userId="me"))
        account = profile.get("emailAddress", "").lower()
        if not self.expected_email or account != self.expected_email:
            self._connection_state("account_mismatch")
            raise EmailUnavailable(
                "Connected Google account does not match the configured Gmail account"
            )
        self._connection_state("verified", email=account)
        return profile

    async def parse_full_message(self, raw, heartbeat=lambda: None):
        # Gmail may move large inline text bodies to the attachments endpoint.
        # Fetch text only; never download or execute file attachments.
        async def hydrate(part):
            if part.get("filename"):
                return
            body = part.get("body", {})
            if (
                part.get("mimeType") in ("text/plain", "text/html")
                and body.get("attachmentId")
                and not body.get("data")
            ):
                heartbeat()
                content = await self._read(
                    lambda: self.client.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=raw["id"], id=body["attachmentId"])
                )
                body["data"] = content.get("data", "")
            for child in part.get("parts", []):
                await hydrate(child)

        await hydrate(raw.get("payload", {}))
        return parse_message(raw)

    async def fetch_unread_emails(self, max_results=5):
        """Compatibility read; the worker uses history sync, not unread-only polling."""
        await self.get_profile()
        data = await self._read(
            lambda: self.client.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=max_results)
        )
        return [
            parse_message(
                await self._read(
                    lambda item=item: self.client.users()
                    .messages()
                    .get(userId="me", id=item["id"], format="full")
                )
            )
            for item in data.get("messages", [])
        ]

    async def send_email(
        self,
        to,
        subject,
        body,
        thread_id=None,
        *,
        purpose="notification",
        company="",
        approval_id=None,
        in_reply_to=None,
        references=None,
        attachment=None,
    ):
        # Preflight happens before recording any network send attempt.
        profile = await self.get_profile()
        if (
            not to
            or "@" not in to
            or not body
            or not subject
            or any(
                "\n" in v or "\r" in v
                for v in (to, subject, in_reply_to or "", references or "")
            )
        ):
            raise EmailUnavailable("Invalid recipient or message headers")
        if thread_id and not in_reply_to:
            raise EmailUnavailable(
                "Reply requires the original Message-ID to preserve the Gmail thread"
            )
        if purpose == "report":
            ensure_eligible(to, purpose)
        record_id = uuid4().hex
        rfc_id = f"<{record_id}.my-agent@{profile['emailAddress'].split('@')[1]}>"
        message = MIMEText(body, _charset="utf-8")
        if attachment:
            if purpose != "report":
                raise EmailUnavailable(
                    "Attachments are only supported for saved reports"
                )
            message = MIMEMultipart("mixed")
            message.attach(MIMEText(body, _charset="utf-8"))
            part = MIMEApplication(
                attachment["content"],
                _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            part.add_header(
                "Content-Disposition", "attachment", filename=attachment["filename"]
            )
            message.attach(part)
        message["To"], message["From"], message["Subject"] = (
            to,
            profile["emailAddress"],
            subject,
        )
        message["Message-ID"], message["Date"] = rfc_id, formatdate(localtime=False)
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = ((references or "") + " " + in_reply_to).strip()
        payload = {
            "raw": base64.urlsafe_b64encode(message.as_bytes(policy=SMTP)).decode(
                "utf-8"
            )
        }
        if thread_id:
            payload["threadId"] = thread_id
        store.put(
            "messages",
            record_id,
            {
                "to": to.lower(),
                "from": profile["emailAddress"].lower(),
                "subject": subject,
                "body": body,
                "purpose": purpose,
                "company": company,
                "thread_id": thread_id,
                "status": "sending",
                "rfc_message_id": rfc_id,
                "approval_id": approval_id,
                "send_controls_version": 1,
                "followup_of": (
                    (store.get("approvals", approval_id) or {}).get("followup_of")
                    if approval_id
                    else None
                ),
            },
        )
        if approval_id:
            store.transition(
                "approvals", approval_id, ["sending"], "sending", dispatch_id=record_id
            )
        try:

            def submit():
                with self._lock:
                    if approval_id or purpose == "report":
                        ensure_eligible(to, purpose)
                    if approval_id:
                        from services.reply_service import validate_queued_reply

                        validate_queued_reply(
                            store.get("approvals", approval_id) or {},
                            self.expected_email,
                        )
                        from services.followups import validate as validate_followup

                        validate_followup(
                            store.get("approvals", approval_id) or {},
                            self.expected_email,
                        )
                    if approval_id and purpose == "outreach":
                        approval = store.get("approvals", approval_id) or {}
                        lead_id = approval.get("lead_id") or (
                            approval.get("lead_data") or {}
                        ).get("id")
                        if lead_id:
                            from services.lead_service import ensure_qualified

                            ensure_qualified(lead_id, to)
                    from services.send_controls import reserve

                    reserve(profile["emailAddress"].lower(), purpose, record_id)
                    return (
                        self.client.users()
                        .messages()
                        .send(userId="me", body=payload)
                        .execute(num_retries=0)
                    )

            sent = await asyncio.to_thread(submit)
            if not sent.get("id") or not sent.get("threadId"):
                raise DeliveryUnknown(
                    "Gmail did not confirm the message and thread IDs"
                )
        except EligibilityError:
            store.transition(
                "messages",
                record_id,
                ["sending"],
                "failed",
                error="Contact became ineligible before submission",
            )
            raise
        except (RefreshError, HttpError) as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if isinstance(exc, RefreshError) or status in (
                400,
                401,
                403,
                404,
                413,
                429,
            ):
                store.transition(
                    "messages",
                    record_id,
                    ["sending"],
                    "failed",
                    error="Gmail rejected this submission",
                )
                if isinstance(exc, RefreshError) or status == 401:
                    self._connection_state("reauthorization_required")
                raise EmailUnavailable(
                    "Gmail rejected the send. Check authorisation, recipient and sending limits before retrying"
                ) from exc
            store.transition("messages", record_id, ["sending"], "delivery_unknown")
            raise DeliveryUnknown(
                "Submission is uncertain. Use Reconcile; do not resend"
            ) from exc
        except Exception as exc:
            store.transition("messages", record_id, ["sending"], "delivery_unknown")
            raise DeliveryUnknown(
                "Submission is uncertain. Use Reconcile; do not resend"
            ) from exc
        store.confirm_submission(record_id, sent["id"], sent["threadId"])
        return {
            "status": "sent",
            "id": sent["id"],
            "thread_id": sent["threadId"],
            "to": to,
            "subject": subject,
        }

    async def sync_mailbox(self, cursor, heartbeat=lambda: None):
        profile = await self.get_profile()
        mailbox = profile["emailAddress"].lower()
        tracked = {
            m["thread_id"]
            for m in store.list("messages")
            if m.get("thread_id")
            and m.get("from") == mailbox
            and m.get("purpose") in ("outreach", "reply", "test")
            and m.get("status") == "sent"
        }
        messages = {}
        saved_threads = (store.get("gmail_cursor", mailbox) or {}).get("thread_ids", [])
        new_threads = tracked - set(saved_threads)
        full = cursor is None
        history_id = profile["historyId"]
        if cursor:
            token = None
            try:
                for _ in range(settings.GMAIL_SYNC_MAX_PAGES):
                    heartbeat()
                    kwargs = {
                        "userId": "me",
                        "startHistoryId": cursor,
                        "historyTypes": ["messageAdded"],
                        "maxResults": 100,
                    }
                    if token:
                        kwargs["pageToken"] = token
                    page = await self._read(
                        lambda kwargs=kwargs: self.client.users()
                        .history()
                        .list(**kwargs)
                    )
                    for change in page.get("history", []):
                        for added in change.get("messagesAdded", []):
                            item = added["message"]
                            if item.get("threadId") in tracked:
                                try:
                                    heartbeat()
                                    raw = await self._read(
                                        lambda item=item: self.client.users()
                                        .messages()
                                        .get(userId="me", id=item["id"], format="full")
                                    )
                                    messages[raw["id"]] = raw
                                except HttpError as exc:
                                    if exc.resp.status != 404:
                                        raise
                    token = page.get("nextPageToken")
                    history_id = page.get("historyId", history_id)
                    if not token:
                        break
                else:
                    raise EmailUnavailable(
                        "Gmail sync page limit reached; cursor was not advanced"
                    )
            except HttpError as exc:
                if exc.resp.status != 404:
                    raise
                full = True
        if full or new_threads:
            # Snapshot history ID was obtained before scanning; later changes replay next time.
            if full:
                history_id = profile["historyId"]
            for thread_id in (tracked if full else new_threads):
                heartbeat()
                try:
                    thread = await self._read(
                        lambda thread_id=thread_id: self.client.users()
                        .threads()
                        .get(userId="me", id=thread_id, format="full")
                    )
                except HttpError as exc:
                    if exc.resp.status == 404:
                        continue
                    raise
                for message in thread.get("messages", []):
                    messages[message["id"]] = message
        parsed = [
            await self.parse_full_message(m, heartbeat) for m in messages.values()
        ]
        return {
            "mailbox": mailbox,
            "history_id": history_id,
            "messages": parsed,
            "full_sync": full,
            "thread_ids": sorted(tracked),
        }

    async def reconcile(self, approval_id):
        approval = store.get("approvals", approval_id)
        if approval is None:
            raise KeyError(approval_id)
        if approval["status"] == "sent":
            return {"status": "sent", "already_sent": True}
        if approval["status"] not in ("sending", "delivery_unknown"):
            raise ValueError("Only held submissions can be reconciled")
        record = store.get("messages", approval.get("dispatch_id", ""))
        if not record or not record.get("rfc_message_id"):
            return {
                "status": "held",
                "message": "This legacy submission has no correlation ID; manual provider review is required",
            }
        profile = await self.get_profile()
        if profile["emailAddress"].lower() != record.get("from"):
            raise EmailUnavailable("This submission belongs to another Gmail account")
        query = f"in:sent rfc822msgid:{record['rfc_message_id']}"
        found = await self._read(
            lambda: self.client.users()
            .messages()
            .list(userId="me", q=query, maxResults=2)
        )
        if len(found.get("messages", [])) != 1:
            return {
                "status": "held",
                "message": "No unique sent message found. The submission remains held; no resend was attempted",
            }
        raw = await self._read(
            lambda: self.client.users()
            .messages()
            .get(userId="me", id=found["messages"][0]["id"], format="full")
        )
        actual = parse_message(raw)
        headers = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }
        if (
            actual["rfc_message_id"] != record["rfc_message_id"]
            or actual["sender"] != record["from"]
            or headers.get("to", "").strip().lower() != record["to"]
            or actual["subject"] != record["subject"]
            or "SENT" not in actual["labels"]
        ):
            return {
                "status": "held",
                "message": "Provider evidence did not match the saved submission",
            }
        store.confirm_submission(record["id"], raw["id"], raw["threadId"])
        return {"status": "sent", "provider_message_id": raw["id"], "reconciled": True}


email_service = GmailServiceAdapter()
