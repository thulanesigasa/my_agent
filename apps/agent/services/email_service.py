"""
Gmail API Service Adapter: Asynchronous integration using google-api-python-client and google-auth.
Handles email fetching, thread context extraction, and sending approved message responses.
"""
import logging
import base64
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger("agent.email_service")


class GmailServiceAdapter:
    """
    Gmail API adapter for querying inbox threads and dispatching approved email drafts.
    """

    def __init__(self):
        self.client = None
        self.is_configured = bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)
        if self.is_configured:
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                creds = Credentials(
                    token=None,
                    refresh_token=settings.GMAIL_REFRESH_TOKEN,
                    client_id=settings.GMAIL_CLIENT_ID,
                    client_secret=settings.GMAIL_CLIENT_SECRET,
                    token_uri="https://oauth2.googleapis.com/token"
                )
                self.client = build("gmail", "v1", credentials=creds)
                logger.info("Gmail API Client successfully initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gmail API Client: {e}. Utilizing mock mode.")

    async def fetch_unread_emails(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch unread inbox messages and thread context.
        """
        if self.client:
            try:
                results = self.client.users().messages().list(
                    userId="me", q="is:unread", maxResults=max_results
                ).execute()
                messages = results.get("messages", [])
                email_list = []
                for msg_meta in messages:
                    msg = self.client.users().messages().get(
                        userId="me", id=msg_meta["id"]
                    ).execute()
                    headers = msg.get("payload", {}).get("headers", [])
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                    snippet = msg.get("snippet", "")
                    email_list.append({
                        "id": msg["id"],
                        "thread_id": msg.get("threadId"),
                        "sender": sender,
                        "subject": subject,
                        "body": snippet
                    })
                return email_list
            except Exception as e:
                logger.error(f"Error fetching unread Gmail messages: {e}")

        # Return structured context sample when unconfigured or testing
        return [
            {
                "id": "msg_101",
                "thread_id": "thread_88101",
                "sender": "client@enterprise.com",
                "subject": "Enterprise Contract Upgrade Request",
                "body": "Hi, we are interested in upgrading our team to the enterprise tier. Can you share custom pricing?"
            }
        ]

    async def send_email(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an approved email draft via Gmail API.
        """
        logger.info(f"Sending approved email to {to} [Subject: '{subject}']...")
        if self.client:
            try:
                message = MIMEText(body)
                message["to"] = to
                message["subject"] = subject
                raw_str = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
                body_payload = {"raw": raw_str}
                if thread_id:
                    body_payload["threadId"] = thread_id

                sent_msg = self.client.users().messages().send(
                    userId="me", body=body_payload
                ).execute()
                return {"status": "sent", "id": sent_msg.get("id"), "to": to, "subject": subject}
            except Exception as e:
                logger.error(f"Error sending email via Gmail API: {e}")

        # Simulated response
        return {"status": "sent_simulated", "to": to, "subject": subject, "thread_id": thread_id}


email_service = GmailServiceAdapter()
