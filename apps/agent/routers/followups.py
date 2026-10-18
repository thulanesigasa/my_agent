"""Private operator-requested follow-up previews and approval drafts."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from core.security import verify_api_key
from core.store import ConflictError
from services import followups
from services.contacts import EligibilityError
from services.email_service import email_service

router = APIRouter(
    prefix="/api/followups", tags=["Follow-ups"], dependencies=[Depends(verify_api_key)]
)


def run(call):
    try:
        return call()
    except KeyError:
        raise HTTPException(404, "Outreach not found for this mailbox")
    except ConflictError as exc:
        raise HTTPException(409, str(exc))
    except EligibilityError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("")
def candidates():
    return followups.list_candidates(email_service.expected_email)


@router.post("/{outbound_id}/preview")
def preview(outbound_id: str):
    return run(lambda: followups.preview(outbound_id, email_service.expected_email))


class DraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=1, max_length=60)
    body: str = Field(min_length=1, max_length=20000)


@router.post("/{outbound_id}/draft")
def draft(outbound_id: str, payload: DraftInput):
    return run(
        lambda: followups.queue(
            outbound_id, email_service.expected_email, payload.preview_id, payload.body
        )
    )
