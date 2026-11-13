"""Atomic, conservative local reservations. Never a claim about provider invoices."""

import json
from datetime import datetime, timezone
from uuid import uuid4
from config import settings
from core.store import store, now


def month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def status():
    used = sum(
        r["pence"] for r in store.list("paid_reservations") if r["month"] == month()
    )
    return {
        "month": month(),
        "limit_pence": settings.MONTHLY_BUDGET_PENCE,
        "fixed_pence": settings.FIXED_COST_RESERVE_PENCE,
        "reserved_pence": used,
        "remaining_pence": max(
            0, settings.MONTHLY_BUDGET_PENCE - settings.FIXED_COST_RESERVE_PENCE - used
        ),
        "warning": "Local estimated reservations only. Set provider caps too; taxes, exchange rates, subscriptions and usage elsewhere are not measured. Failed or uncertain requests retain their reservation.",
    }


def reserve(kind, pence):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        values = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT data FROM records WHERE kind='paid_reservations'"
            )
        ]
        used = sum(v["pence"] for v in values if v["month"] == month())
        if (
            used + pence + settings.FIXED_COST_RESERVE_PENCE
            > settings.MONTHLY_BUDGET_PENCE
        ):
            raise ValueError(
                "Local monthly spending allowance reached; no provider request made"
            )
        key = uuid4().hex
        value = {
            "id": key,
            "kind": kind,
            "month": month(),
            "pence": pence,
            "created_at": now(),
        }
        db.execute(
            "INSERT INTO records VALUES ('paid_reservations',?,?)",
            (key, json.dumps(value)),
        )
    return key
