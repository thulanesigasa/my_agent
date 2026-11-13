"""Authenticated Gmail push triggers the same history sync used by polling.

Native Pub/Sub verifies Google signatures, audience and service-account identity.
A shared-secret relay remains available when OIDC settings are absent.
"""

import asyncio
import base64
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request
from config import settings
from services.inbox_service import process_inbox_batch
from services.email_service import email_service
from core.store import ConflictError


def verify_oidc(token):
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request as GoogleRequest

    return id_token.verify_oauth2_token(
        token, GoogleRequest(), audience=settings.PUBSUB_AUDIENCE
    )


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
    request: Request,
    x_goog_pubsub_token: str = Header("", alias="X-Goog-PubSub-Token"),
    authorization: str = Header(""),
):
    if settings.PUBSUB_AUDIENCE or settings.PUBSUB_SERVICE_ACCOUNT_EMAIL:
        if not settings.PUBSUB_AUDIENCE or not settings.PUBSUB_SERVICE_ACCOUNT_EMAIL:
            raise HTTPException(
                status_code=503,
                detail="Both Pub/Sub audience and service-account email must be configured",
            )
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=403, detail="Missing Pub/Sub bearer token")
        try:
            claims = await asyncio.to_thread(verify_oidc, authorization[7:])
            if (
                claims.get("email") != settings.PUBSUB_SERVICE_ACCOUNT_EMAIL
                or claims.get("email_verified") is not True
            ):
                raise ValueError("Unexpected service account")
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid Pub/Sub identity")
    elif not settings.WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Gmail webhook is disabled until authentication is configured",
        )
    elif not verify_pubsub_token(None, x_goog_pubsub_token):
        raise HTTPException(status_code=403, detail="Invalid webhook token")
    try:
        payload = await request.json()
        data = json.loads(base64.b64decode(payload["message"]["data"], validate=True))
        if not isinstance(data.get("historyId"), (str, int)) or not isinstance(
            data.get("emailAddress"), str
        ):
            raise ValueError("Missing Gmail notification fields")
        expected = email_service.expected_email or settings.GMAIL_USER_EMAIL
        if not expected or data["emailAddress"].lower() != expected.lower():
            raise ValueError("Unexpected mailbox")
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid Gmail notification")
    try:
        result = await process_inbox_batch()
    except ConflictError:
        # Existing owner will consume the same persisted history cursor. Retry later.
        raise HTTPException(
            status_code=503, detail="Mailbox sync busy; retry notification"
        )
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
