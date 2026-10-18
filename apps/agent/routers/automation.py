"""Private setup and recorded status for approval-only automation."""

from fastapi import APIRouter, Depends, HTTPException
from core.security import verify_api_key
from core.store import ConflictError
from services import automation
from services.email_service import email_service

router = APIRouter(
    prefix="/api/automation",
    tags=["Automation"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("")
def status():
    return automation.listing(email_service.expected_email)


@router.patch("")
def configure(payload: automation.AutomationInput):
    try:
        return automation.update(payload, email_service.expected_email)
    except ConflictError as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
