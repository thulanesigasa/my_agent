"""Local portfolio matching and proposal previews. No provider or model calls."""

import json
import re
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from core.store import store, now, ConflictError
from services.contacts import EligibilityError
from services.lead_service import ensure_qualified, public_url

SEED = Path(__file__).resolve().parents[1] / "resources" / "portfolio.json"
CONTACT_EMAIL = "pharezsigasa@gmail.com"
CONTACT_PHONE = "+447544357979"


def single_line(value):
    return " ".join(value.split())


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9-]{1,60}$")
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=2000)
    description: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)
    active: bool = True

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        return public_url(value)

    @field_validator("name", "description")
    @classmethod
    def clean_text(cls, value):
        if "\r" in value or "\n" in value or (value and not value.strip()):
            raise ValueError("Use non-blank single-line text")
        return value.strip()

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values):
        tags = []
        for value in values:
            value = single_line(value).casefold()
            if not value or len(value) > 60:
                raise ValueError("Each industry tag must have 1–60 characters")
            if value not in tags:
                tags.append(value)
        return tags


class Portfolio(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(default=0, ge=0)
    agency_name: str = Field(min_length=1, max_length=100)
    portfolio_url: str = Field(max_length=2000)
    projects: list[Project] = Field(max_length=12)

    @field_validator("agency_name")
    @classmethod
    def clean_name(cls, value):
        return Project.clean_text(value)

    @field_validator("portfolio_url")
    @classmethod
    def check_url(cls, value):
        return public_url(value)

    @model_validator(mode="after")
    def unique_ids(self):
        if len({p.id for p in self.projects}) != len(self.projects):
            raise ValueError("Project IDs must be unique")
        return self


def portfolio():
    saved = store.get("portfolio", "current")
    return Portfolio.model_validate(
        saved["catalog"] if saved else json.loads(SEED.read_text())
    ).model_dump()


def save_portfolio(payload: Portfolio):
    # Revision check and replacement share a write transaction across API processes.
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT data FROM records WHERE kind='portfolio' AND id='current'"
        ).fetchone()
        current = json.loads(row[0])["catalog"] if row else {"version": 0}
        if current["version"] != payload.version:
            raise ConflictError("Portfolio changed; reload before saving")
        catalog = {**payload.model_dump(), "version": payload.version + 1}
        db.execute(
            "INSERT INTO records VALUES ('portfolio', 'current', ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (json.dumps({"catalog": catalog, "updated_at": now()}),),
        )
    return catalog


def match_projects(lead, catalog):
    # Match whole words/phrases only against the saved industry, never page instructions.
    industry = " ".join(re.findall(r"\w+", lead.get("industry", "").casefold()))
    ranked = []
    for index, project in enumerate(catalog["projects"]):
        if not project["active"]:
            continue
        matches = [
            tag
            for tag in project["tags"]
            if (phrase := " ".join(re.findall(r"\w+", tag)))
            and f" {phrase} " in f" {industry} "
        ]
        ranked.append((len(matches), index, project, matches))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    has_match = any(item[0] for item in ranked)
    return [
        {
            **project,
            "reason": (
                "Configured industry tags: " + ", ".join(tags)
                if score
                else "General portfolio example; no configured industry match"
            ),
        }
        for score, _, project, tags in ranked
        if not has_match or score
    ][:2]


def create_preview(lead_id, mailbox):
    lead = ensure_qualified(lead_id)
    if not mailbox:
        raise EligibilityError("Connect Gmail before creating outreach drafts")
    catalog = portfolio()
    projects = match_projects(lead, catalog)
    name = single_line(lead["review"].get("confirmed_name") or lead["name"])
    location = single_line(lead.get("location", ""))
    agency = catalog["agency_name"]
    examples = "\n".join(
        f"- {p['name']}: {p['url']}"
        + (f"\n  {p['description']}" if p["description"] else "")
        for p in projects
    )
    body = (
        f"Hi {name} team,\n\n"
        f"I'm reaching out from {agency} about a website for your business in {location}. "
        "We couldn't find an independent website in the sources we reviewed. Please let us know if we missed it.\n\n"
        "We can discuss a website that presents your services and gives customers a clear way to contact you.\n\n"
        f"Our portfolio: {catalog['portfolio_url']}\n"
        + (f"Some projects we've developed:\n{examples}\n\n" if projects else "\n")
        + "Would you be open to discussing what you need? We can prepare a quotation once we understand the scope.\n\n"
        f"Best,\n{agency}\n{CONTACT_EMAIL} | {CONTACT_PHONE}\n\n"
        "If you'd prefer no further outreach, reply 'unsubscribe'."
    )
    return store.put(
        "proposal_previews",
        uuid4().hex,
        {
            "lead_id": lead_id,
            "lead_revision": lead["revision"],
            "sender_mailbox": mailbox,
            "recipient_email": lead["review"]["email"],
            "portfolio_version": catalog["version"],
            "portfolio_url": catalog["portfolio_url"],
            "projects": projects,
            "subject": f"Website enquiry for {name}",
            "body": body,
            "template_version": 1,
        },
    )


def preview_snapshot(preview_id, lead, mailbox, subject, body):
    preview = store.get("proposal_previews", preview_id)
    if not preview or preview["lead_id"] != lead["id"]:
        raise ValueError("Proposal preview does not belong to this lead")
    if (
        preview["lead_revision"] != lead["revision"]
        or preview["sender_mailbox"] != mailbox
        or preview["recipient_email"] != lead["review"]["email"]
        or preview["portfolio_version"] != portfolio()["version"]
    ):
        raise ConflictError(
            "Lead, mailbox or portfolio changed; generate a new proposal"
        )
    return {
        **preview,
        "edited_before_queue": subject != preview["subject"] or body != preview["body"],
    }
