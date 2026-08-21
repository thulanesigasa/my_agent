"""
WhatsApp Integration Service: Twilio API adapter for WhatsApp messaging and webhook parsing.
"""
import logging
from typing import Dict, Any, Optional
from config import settings

logger = logging.getLogger("agent.whatsapp_service")


class WhatsAppServiceAdapter:
    """
    Twilio WhatsApp Service Adapter for sending replies and parsing webhook payloads.
    """

    def __init__(self):
        self.is_configured = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
        self.client = None
        if self.is_configured:
            try:
                from twilio.rest import Client
                self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                logger.info("Twilio WhatsApp Client successfully initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize Twilio client: {e}. Utilizing fallback mode.")

    async def send_whatsapp_message(self, to_number: str, message_body: str) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Twilio API.
        """
        recipient = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        logger.info(f"Sending WhatsApp message to {recipient}...")

        if self.client and settings.TWILIO_WHATSAPP_NUMBER:
            try:
                msg = self.client.messages.create(
                    from_=settings.TWILIO_WHATSAPP_NUMBER,
                    body=message_body,
                    to=recipient
                )
                return {"status": "sent", "sid": msg.sid, "to": recipient}
            except Exception as e:
                logger.error(f"Error sending WhatsApp message via Twilio: {e}")

        return {"status": "sent_simulated", "to": recipient, "body": message_body}

    @staticmethod
    def parse_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses incoming Twilio WhatsApp webhook payload to extract sender, body, and media URLs.
        """
        sender = payload.get("From", "").replace("whatsapp:", "")
        body = payload.get("Body", "")
        media_url = payload.get("MediaUrl0")
        num_media = int(payload.get("NumMedia", 0))

        return {
            "sender": sender,
            "body": body,
            "media_url": media_url if num_media > 0 else None,
            "has_media": num_media > 0,
            "raw_payload": payload
        }


whatsapp_service = WhatsAppServiceAdapter()
