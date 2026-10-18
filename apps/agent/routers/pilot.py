"""Private read-only pilot evidence."""

from fastapi import APIRouter, Depends
from core.security import verify_api_key
from services.email_service import email_service
from services.pilot import readiness

router = APIRouter(
    prefix="/api/pilot", tags=["Pilot"], dependencies=[Depends(verify_api_key)]
)


@router.get("/readiness")
def get_readiness():
    return readiness(email_service.expected_email)
