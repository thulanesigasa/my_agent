"""Private, approval-only campaign drafting controls."""

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from core.security import verify_api_key
from core.store import ConflictError
from config import settings
from services import campaigns
from services.contacts import EligibilityError
from services.email_service import email_service

router = APIRouter(
    prefix="/api/campaigns", tags=["Campaigns"], dependencies=[Depends(verify_api_key)]
)


def operation(call):
    try:
        return call()
    except KeyError:
        raise HTTPException(404, "Campaign or lead not found for this mailbox")
    except ConflictError as exc:
        raise HTTPException(409, str(exc))
    except EligibilityError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception:
        raise HTTPException(
            503,
            "Campaign drafting failed locally; review its state and run history",
        )


@router.get("")
def listing():
    return {
        **campaigns.listing(email_service.expected_email),
        "worker_enabled": settings.CAMPAIGNS_ENABLED,
    }


@router.post("")
def create(payload: campaigns.CampaignInput):
    return operation(lambda: campaigns.create(payload, email_service.expected_email))


class ControlInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["pause", "resume", "cancel"]
    version: int = Field(ge=0)


@router.patch("/{campaign_id}")
def control(campaign_id: str, payload: ControlInput):
    return operation(
        lambda: campaigns.control(
            campaign_id, email_service.expected_email, payload.action, payload.version
        )
    )


@router.post("/{campaign_id}/run")
def run(campaign_id: str):
    return operation(
        lambda: campaigns.run_campaign(campaign_id, email_service.expected_email)
    )
