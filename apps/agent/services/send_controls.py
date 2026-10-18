"""Durable business-send pause and per-mailbox SAST daily attempt reservations."""

import json
from datetime import datetime, timedelta, time, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from core.store import store, now, ConflictError
from services.contacts import EligibilityError
from services.report_service import TZ, instant

BUSINESS_PURPOSES = ("outreach", "reply")
DEFAULT = {"version": 0, "paused": False, "daily_limit": 5}


class Controls(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=0)
    paused: bool
    daily_limit: int = Field(ge=1, le=25)


def _config(db):
    row = db.execute(
        "SELECT data FROM records WHERE kind='send_controls' AND id='current'"
    ).fetchone()
    return json.loads(row[0])["config"] if row else dict(DEFAULT)


def update(payload):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if _config(db)["version"] != payload.version:
            raise ConflictError("Sending controls changed; reload before saving")
        config = {**payload.model_dump(), "version": payload.version + 1}
        db.execute(
            "INSERT INTO records VALUES ('send_controls','current',?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (json.dumps({"config": config, "updated_at": now()}),),
        )
        db.execute(
            "INSERT INTO activity VALUES (?,?,?,?,?)",
            (
                uuid4().hex,
                "sending.controls_changed",
                "current",
                now(),
                json.dumps(config),
            ),
        )
    return config


def _usage(db, mailbox, at):
    day = at.astimezone(TZ).date()
    reservations = [
        json.loads(r[0])
        for r in db.execute(
            "SELECT data FROM records WHERE kind='send_attempts'"
        ).fetchall()
    ]
    current = [
        r for r in reservations if r["mailbox"] == mailbox and r["day"] == str(day)
    ]
    # Upgrading must not erase today's already-confirmed or uncertain business sends.
    legacy = []
    for row in db.execute("SELECT data FROM records WHERE kind='messages'").fetchall():
        message = json.loads(row[0])
        sent = instant(message.get("created_at"))
        if (
            not message.get("send_controls_version")
            and message.get("from") == mailbox
            and message.get("purpose") in BUSINESS_PURPOSES
            and message.get("status") in ("sending", "delivery_unknown", "sent")
            and sent
            and sent.astimezone(TZ).date() == day
        ):
            legacy.append(message)
    config = _config(db)
    used = len(current) + len(legacy)
    return {
        "config": config,
        "mailbox": mailbox or "",
        "day": str(day),
        "timezone": str(TZ),
        "reserved_attempts": len(current),
        "legacy_submissions": len(legacy),
        "used": used,
        "remaining": max(0, config["daily_limit"] - used),
        "resets_at": datetime.combine(
            day + timedelta(days=1), time.min, TZ
        ).isoformat(),
    }


def status(mailbox, *, at=None):
    with store.connect() as db:
        db.execute("BEGIN")
        return _usage(db, mailbox, at or datetime.now(timezone.utc))


def _allowed(usage):
    if usage["config"]["paused"]:
        raise EligibilityError(
            "Business sending is paused. Resume it in Settings → Sending controls"
        )
    if usage["remaining"] <= 0:
        raise EligibilityError(
            "Daily business-send attempt limit reached. Review Sending controls; allowance resets at midnight SAST"
        )


def check_available(mailbox, purpose):
    if purpose in BUSINESS_PURPOSES:
        _allowed(status(mailbox))


def reserve(mailbox, purpose, dispatch_id, *, at=None):
    if purpose not in BUSINESS_PURPOSES:
        return None  # Owned-mailbox connection tests and report attachments retain their own checks.
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute(
            "SELECT 1 FROM records WHERE kind='send_attempts' AND id=?", (dispatch_id,)
        ).fetchone():
            raise EligibilityError(
                "This submission attempt was already reserved; do not replay it"
            )
        usage = _usage(db, mailbox, at or datetime.now(timezone.utc))
        _allowed(usage)
        value = {
            "id": dispatch_id,
            "mailbox": mailbox,
            "purpose": purpose,
            "day": usage["day"],
            "created_at": now(),
        }
        db.execute(
            "INSERT INTO records VALUES ('send_attempts',?,?)",
            (dispatch_id, json.dumps(value)),
        )
        db.execute(
            "INSERT INTO activity VALUES (?,?,?,?,?)",
            (
                uuid4().hex,
                "sending.reserved",
                dispatch_id,
                now(),
                json.dumps({"purpose": purpose, "day": usage["day"]}),
            ),
        )
    return value
