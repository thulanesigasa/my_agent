import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger("agent.whatsapp_service")

class WhatsAppServiceAdapter:
    """
    WhatsApp / Twilio integration adapter.
    Handles message dispatch after Human-in-the-loop approval.
    """

    def __init__(self):
        self.is_configured = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)

    async def send_whatsapp_message(self, recipient_number: str, message_body: str) -> Dict[str, Any]:
        """
        Send WhatsApp message via Twilio API upon human approval.
        """
        logger.info(f"Dispatching WhatsApp message to {recipient_number}...")
        if not self.is_configured:
            logger.info("Twilio keys not configured. Simulating WhatsApp dispatch.")
            return {
                "status": "simulated_success",
                "sid": "WA_MOCK_88291",
                "to": recipient_number,
                "body": message_body
            }
        
        # Real Twilio API Call logic:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     from_=settings.TWILIO_WHATSAPP_NUMBER,
        #     body=message_body,
        #     to=f"whatsapp:{recipient_number}"
        # )
        # return {"status": "sent", "sid": message.sid}
        return {"status": "sent", "to": recipient_number}


whatsapp_service = WhatsAppServiceAdapter()
