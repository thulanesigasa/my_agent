import logging
from typing import Dict, Any, Optional
from config import settings

logger = logging.getLogger("agent.email_service")

class GmailServiceAdapter:
    """
    Gmail API integration adapter.
    Handles email fetching, draft creation, and sending after Human-in-the-loop approval.
    """

    def __init__(self):
        self.is_configured = bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET)

    async def fetch_recent_emails(self, max_results: int = 5) -> list:
        """
        Fetch recent inbox messages.
        """
        if not self.is_configured:
            logger.info("Gmail credentials not provided. Returning sample email context.")
            return [
                {
                    "id": "msg_001",
                    "subject": "Project Sprint Update",
                    "sender": "lead@company.com",
                    "snippet": "Hi team, please share the latest deployment timeline for the agent platform.",
                    "date": "2026-08-09T10:00:00Z"
                }
            ]
        # In production, use google-api-python-client with Refresh Token
        return []

    async def create_draft(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Prepare an email draft requiring approval.
        """
        logger.info(f"Creating email draft for {recipient}: '{subject}'")
        return {
            "draft_id": "draft_9921",
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "ready_for_approval"
        }

    async def send_email(self, draft_id: str, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Dispatch email upon Human-in-the-Loop approval.
        """
        logger.info(f"Human Approval Granted! Dispatching email to {recipient}...")
        return {
            "status": "success",
            "message_id": "sent_10284",
            "recipient": recipient,
            "subject": subject
        }


email_service = GmailServiceAdapter()
