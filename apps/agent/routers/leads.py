"""Private lead discovery, evidence review and controlled outreach draft APIs."""

import csv
from io import StringIO
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from core.security import verify_api_key
from core.store import store, ConflictError
from config import settings
from services.contacts import EligibilityError, normalize_email
from services.email_service import email_service
from services.lead_service import (
    ingest_candidate,
    review_lead,
    lead_view,
    draft_lead,
    public_url,
)
from services.lead_discovery import (
    discover_osm,
    DiscoveryUnavailable,
    ResearchCooldown,
    ATTRIBUTION,
    provider_info,
    cooldown_remaining,
)

router = APIRouter(
    prefix="/api/leads", tags=["Leads"], dependencies=[Depends(verify_api_key)]
)


def failure(exc):
    if isinstance(exc, KeyError):
        raise HTTPException(404, "Lead not found")
    if isinstance(exc, ResearchCooldown):
        raise HTTPException(
            409,
            {"message": str(exc), "retry_after_seconds": exc.retry_after},
            headers={"Retry-After": str(exc.retry_after)},
        )
    if isinstance(exc, ConflictError):
        raise HTTPException(409, str(exc))
    if isinstance(exc, EligibilityError):
        raise HTTPException(403, str(exc))
    if isinstance(exc, DiscoveryUnavailable):
        delay = exc.retry_after or cooldown_remaining()
        raise HTTPException(
            503,
            {"message": str(exc), "retry_after_seconds": delay},
            headers={"Retry-After": str(delay)} if delay else None,
        )
    if isinstance(exc, ValueError):
        raise HTTPException(400, str(exc))
    raise exc


@router.get("")
def leads():
    return {
        "leads": [lead_view(lead) for lead in reversed(store.list("leads"))],
        "attribution": ATTRIBUTION,
        "daily_limit": settings.OSM_DAILY_QUERY_LIMIT,
        "max_radius_km": 5,
        "provider": provider_info(),
        "retry_after_seconds": cooldown_remaining(),
    }


class CandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)
    source_url: str = Field(min_length=1, max_length=2000)
    address: str = Field(default="", max_length=500)
    phone: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=300)
    website: str = Field(default="", max_length=2000)
    industry: str = Field(default="", max_length=200)


def candidate_data(payload):
    data = payload.model_dump()
    data["source_url"] = public_url(data["source_url"])
    if data["email"]:
        data["email"] = normalize_email(data["email"])
    if data["website"]:
        data["website"] = public_url(data["website"])
    if not data["name"].strip() or not data["location"].strip():
        raise ValueError("Business name and location cannot be blank")
    return {**data, "source": "manual"}


@router.post("")
def add_lead(payload: CandidateInput):
    try:
        return lead_view(ingest_candidate(candidate_data(payload)))
    except ValueError as exc:
        failure(exc)


class CSVInput(BaseModel):
    csv_text: str = Field(min_length=1, max_length=200000)


@router.post("/import")
def import_csv(payload: CSVInput):
    try:
        reader = csv.DictReader(StringIO(payload.csv_text.lstrip("\ufeff")))
        columns = reader.fieldnames or []
        if not {"name", "location", "source_url"} <= set(columns) or not set(
            columns
        ) <= set(CandidateInput.model_fields):
            raise ValueError(
                "CSV requires name,location,source_url; optional columns: address,phone,email,website,industry"
            )
        validated = []
        for line, row in enumerate(reader, 2):
            if line > 101:
                raise ValueError("Import at most 100 rows per request")
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"CSV row {line} has the wrong number of columns")
            try:
                validated.append(candidate_data(CandidateInput(**row)))
            except ValueError:
                raise ValueError(
                    f"Invalid CSV row {line}; check required fields, email, lengths and public source URLs"
                )
        if not validated:
            raise ValueError("CSV contains no business rows")
        # Validate the complete file before writing any row.
        imported = {}
        for data in validated:
            lead = ingest_candidate(data)
            imported[lead["id"]] = lead
        return {
            "rows": len(validated),
            "unique_leads": len(imported),
            "lead_ids": list(imported),
        }
    except ValueError as exc:
        failure(exc)


class DiscoveryInput(BaseModel):
    location: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-85, le=85, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    radius_km: float = Field(default=1, ge=0.1, le=5, allow_inf_nan=False)
    category: Literal["all", "shops", "food", "services"] = "all"
    limit: int = Field(default=25, ge=1, le=50)


@router.post("/discover")
async def discover(payload: DiscoveryInput):
    try:
        return await discover_osm(**payload.model_dump())
    except (ValueError, ConflictError, DiscoveryUnavailable) as exc:
        failure(exc)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0)
    identity_verified: bool = False
    identity_source: str = Field(default="", max_length=2000)
    identity_note: str = Field(default="", max_length=2000)
    business_status: Literal["unknown", "active", "inactive"] = "unknown"
    activity_method: Literal[
        "", "recent_public_activity", "direct_confirmation", "local_observation"
    ] = ""
    activity_date: str = Field(default="", max_length=10)
    website_status: Literal[
        "not_checked",
        "found",
        "not_found_after_review",
        "owner_confirmed_none",
        "social_only",
        "uncertain",
    ] = "not_checked"
    website_url: str = Field(default="", max_length=2000)
    website_source: str = Field(default="", max_length=2000)
    website_note: str = Field(default="", max_length=2000)
    contact_verified: bool = False
    email: str = Field(default="", max_length=300)
    contact_source: str = Field(default="", max_length=2000)
    contact_note: str = Field(default="", max_length=2000)
    decision: Literal["needs_review", "qualified", "rejected"] = "needs_review"
    decision_note: str = Field(default="", max_length=2000)


@router.put("/{lead_id}/review")
def review(lead_id: str, payload: ReviewInput):
    try:
        return lead_view(review_lead(lead_id, payload.model_dump()))
    except (ValueError, KeyError) as exc:
        failure(exc)


class DraftInput(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)


@router.post("/{lead_id}/draft")
def draft(lead_id: str, payload: DraftInput):
    try:
        if not payload.subject.strip() or not payload.body.strip():
            raise ValueError("Subject and message cannot be blank")
        return draft_lead(
            lead_id, payload.subject, payload.body, email_service.expected_email
        )
    except (ValueError, KeyError) as exc:
        failure(exc)
