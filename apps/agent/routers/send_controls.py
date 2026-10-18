"""Private business-send policy and current mailbox usage."""

from fastapi import APIRouter, Depends, HTTPException
from core.security import verify_api_key
from core.store import ConflictError
from services import send_controls
from services.email_service import email_service

router = APIRouter(
    prefix="/api/sending-controls",
    tags=["Sending controls"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("")
def get_status():
    return send_controls.status(email_service.expected_email)


@router.put("")
def update(payload: send_controls.Controls):
    try:
        send_controls.update(payload)
        return send_controls.status(email_service.expected_email)
    except ConflictError as exc:
        raise HTTPException(409, str(exc))
