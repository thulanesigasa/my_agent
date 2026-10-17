"""Gmail push ingress with fail-closed shared-secret verification.

Use a trusted relay that injects X-Goog-PubSub-Token. This is shared-secret
verification, not Google identity verification; native authenticated Pub/Sub OIDC
and history cursor synchronisation belong to the email integration phase.
"""

import base64
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request
from config import settings
from services.inbox_service import process_inbox_batch

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def verify_pubsub_token(token, goog_token):
    # Do not accept secrets in query strings or token substrings.
    return bool(
        settings.WEBHOOK_SECRET
        and goog_token
        and hmac.compare_digest(goog_token.encode(), settings.WEBHOOK_SECRET.encode())
    )


@router.post("/gmail")
async def gmail_pubsub_webhook(
    request: Request, x_goog_pubsub_token: str = Header("", alias="X-Goog-PubSub-Token")
):
    if not settings.WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Gmail webhook is disabled until WEBHOOK_SECRET is configured",
        )
    if not verify_pubsub_token(None, x_goog_pubsub_token):
        raise HTTPException(status_code=403, detail="Invalid webhook token")
    try:
        payload = await request.json()
        data = json.loads(base64.b64decode(payload["message"]["data"], validate=True))
        if not isinstance(data.get("historyId"), (str, int)) or not isinstance(
            data.get("emailAddress"), str
        ):
            raise ValueError("Missing Gmail notification fields")
        if (
            settings.GMAIL_USER_EMAIL
            and data["emailAddress"].lower() != settings.GMAIL_USER_EMAIL.lower()
        ):
            raise ValueError("Unexpected mailbox")
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid Gmail notification")
    try:
        result = await process_inbox_batch()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Inbox processing unavailable; notification was not acknowledged",
        )
    if result["failed"]:
        raise HTTPException(
            status_code=503,
            detail="Inbox processing failed; inspect held inbox records",
        )
    return {"status": "ok", **result}
