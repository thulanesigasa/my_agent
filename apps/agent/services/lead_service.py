"""Evidence-based lead ledger. Discovery is an observation, never verification."""

import hashlib
import json
import re
import time
from urllib.parse import urlsplit, urlunsplit, unquote
from uuid import uuid4
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from core.store import store, now, ConflictError
from services.contacts import normalize_email, ensure_eligible, EligibilityError

WEBSITE_STATES = (
    "not_checked",
    "found",
    "not_found_after_review",
    "owner_confirmed_none",
    "social_only",
    "uncertain",
)
TARGET_STATES = ("not_found_after_review", "owner_confirmed_none", "social_only")
MAX_EVIDENCE_AGE = timedelta(days=30)


def observation_fingerprint(lead):
    observation = {
        k: v for k, v in (lead.get("observation") or {}).items() if k != "observed_at"
    }
    return hashlib.sha256(
        json.dumps(
            {"source_url": lead.get("source_url"), "observation": observation},
            sort_keys=True,
        ).encode()
    ).hexdigest()


def normalize_inspection(inspection):
    """Presentation cleanup also applies to old cached findings without a new call."""
    findings = dict(inspection["findings"])
    phones, seen = [], set()
    for item in findings.get("phones", []):
        digits = re.sub(r"\D", "", item["value"])
        if len(digits) == 10 and digits.startswith("0"):
            digits = "27" + digits[1:]
        if len(digits) != 11 or not digits.startswith("27") or digits in seen:
            continue
        seen.add(digits)
        phones.append({**item, "value": "+" + digits})
    findings["phones"] = phones[:10]
    links, external, seen = [], [], set()
    source_host = (urlsplit(inspection["source_url"]).hostname or "").removeprefix(
        "www."
    )
    for item in findings.get("links", []) + findings.get("external_links", []):
        try:
            url = public_url(item["value"])
        except ValueError:
            continue
        parts = urlsplit(url)
        if re.search(
            r"\.(?:png|jpe?g|gif|webp|svg|ico|avif|bmp|css|js|woff2?|ttf|eot|mp[34]|webm|wav|pdf|zip)$",
            unquote(parts.path),
            re.I,
        ):
            continue
        if url in seen or url == inspection["source_url"]:
            continue
        seen.add(url)
        target = (
            links
            if (parts.hostname or "").removeprefix("www.") == source_host
            else external
        )
        if len(target) < 10:
            target.append({**item, "value": url})
    findings["links"], findings["external_links"] = links, external
    return {**inspection, "findings": findings}


def activity_blockers(review):
    blockers = []
    method = review.get("activity_method")
    if method not in (
        "recent_public_activity",
        "direct_confirmation",
        "local_observation",
    ):
        blockers.append("Record how current business activity was verified")
    try:
        observed = date.fromisoformat(review.get("activity_date", ""))
        today = datetime.now(ZoneInfo("Africa/Johannesburg")).date()
        if not 0 <= (today - observed).days <= 30:
            raise ValueError("stale or future")
    except (TypeError, ValueError):
        blockers.append(
            "Record an activity evidence date within the last 30 days (SAST)"
        )
    if method == "recent_public_activity":
        host = (
            (urlsplit(review.get("identity_source", "")).hostname or "")
            .lower()
            .rstrip(".")
        )
        if host in ("openstreetmap.org", "osm.org") or host.endswith(
            (".openstreetmap.org", ".osm.org")
        ):
            blockers.append(
                "A map listing alone is not current activity evidence; use a dated business source or direct/local confirmation"
            )
    return blockers


def source_freshness(observation):
    """Map-edit age is a warning, never proof of business activity or closure."""
    value = observation.get("source_updated_at", "")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - stamp
        if age < timedelta(0):
            raise ValueError("future")
    except (TypeError, ValueError):
        return {"status": "unknown", "age_days": None}
    return {"status": "old" if age.days > 365 else "recent_edit", "age_days": age.days}


def public_url(value):
    value = value.strip()
    if len(value) > 2000:
        raise ValueError("Source URL is too long")
    parts = urlsplit(value)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError("Use a public http(s) source URL without credentials")
    host = parts.hostname.lower()
    if (
        "." not in host
        or host in ("localhost", "localhost.localdomain")
        or host.endswith((".local", ".internal"))
    ):
        raise ValueError("Use a public source URL")
    import ipaddress

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError("Use a public source URL")
    if any(c.isspace() for c in host) or any(c in value for c in "\r\n\t"):
        raise ValueError("Use a valid public source URL")
    try:
        if parts.port not in (None, 80, 443):
            raise ValueError("Use a standard public web URL")
    except ValueError:
        raise ValueError("Use a standard public web URL")
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc.lower(),
            parts.path or "/",
            parts.query,
            parts.fragment,
        )
    )


def normalized(value):
    return re.sub(r"\s+", " ", str(value).strip().casefold())


def candidate_id(candidate):
    if candidate.get("source") == "tavily":
        # A result is a source page, not an established business identity. Preserve
        # legacy result IDs and operator reviews if a page title/query changes.
        existing = next(
            (
                lead
                for lead in store.list("leads")
                if lead.get("source") == "tavily"
                and lead.get("source_url") == candidate["source_url"]
            ),
            None,
        )
        if existing:
            return existing["id"]
        identity = "tavily:" + candidate["source_url"]
    elif candidate.get("source") == "openstreetmap" and re.fullmatch(
        r"(node|way|relation)/\d+", candidate.get("source_id", "")
    ):
        identity = "osm:" + candidate["source_id"]
    else:
        identity = "|".join(
            normalized(candidate.get(k, ""))
            for k in ("name", "location", "address", "phone")
        )
        if (
            not candidate.get("address", "").strip()
            and not candidate.get("phone", "").strip()
        ):
            # Without branch facts, two same-name businesses from different sources
            # are only possible duplicates, not established identical businesses.
            identity += "|" + candidate["source_url"]
    return hashlib.sha256(identity.encode()).hexdigest()[:24]


def ingest_candidate(candidate):
    candidate = {
        k: candidate.get(k, "")
        for k in (
            "name",
            "location",
            "address",
            "phone",
            "email",
            "website",
            "industry",
            "source",
            "source_id",
            "source_url",
            "source_updated_at",
            "source_check_date",
            "source_kind",
            "source_note",
        )
    }
    if not candidate["name"].strip() or not candidate["location"].strip():
        raise ValueError("Business name and location are required")
    candidate["source_url"] = public_url(candidate["source_url"])
    candidate["source"] = candidate["source"] or "manual"
    record_id = candidate_id(candidate)
    observed = {**candidate, "observed_at": now()}
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT data FROM records WHERE kind='leads' AND id=?", (record_id,)
        ).fetchone()
        previous = json.loads(row[0]) if row else {}
        prior = previous.get("observation", {})
        changed = bool(prior) and any(
            prior.get(k, "") != candidate[k] for k in candidate
        )
        value = {
            **previous,
            "id": record_id,
            "name": (previous.get("review") or {}).get("confirmed_name")
            or candidate["name"],
            "location": candidate["location"],
            "address": candidate["address"],
            "phone": candidate["phone"],
            "industry": candidate["industry"],
            "source": candidate["source"],
            "source_url": candidate["source_url"],
            "source_id": candidate["source_id"],
            "observation": observed,
            "created_at": previous.get("created_at", now()),
            "updated_at": now(),
            "last_seen_at": now(),
            "revision": previous.get("revision", 0) + 1,
            "review": previous.get("review"),
            "status": previous.get("status", "needs_review"),
            "requires_review": previous.get("requires_review", True),
            "missing_website": None,
        }
        if changed:
            value.update(
                status=(
                    "rejected"
                    if previous.get("status") == "rejected"
                    else "needs_review"
                ),
                requires_review=True,
                review_invalidated=True,
            )
        # Reimport cannot rewrite operator evidence or resurrect a rejected record.
        history = previous.get("observations", [])
        if not prior or changed:
            history = (history + [observed])[-20:]
        value["observations"] = history
        db.execute(
            "INSERT INTO records VALUES ('leads', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
            (record_id, json.dumps(value)),
        )
        db.execute(
            "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
            (uuid4().hex, "leads.observed", record_id, now(), "{}"),
        )
    return value


def review_blockers(review):
    blockers = []
    if not review.get("identity_verified"):
        blockers.append("Verify that the sources describe this business and branch")
    if review.get("business_status") != "active":
        blockers.append("Confirm the business is active")
    blockers.extend(activity_blockers(review))
    if review.get("website_status") not in TARGET_STATES:
        blockers.append(
            "Review website evidence; existing or uncertain websites are not qualified"
        )
    if not review.get("contact_verified") or not review.get("email"):
        blockers.append("Verify a sourced contact email")
    for key, label in (
        ("identity", "identity"),
        ("website", "website search"),
        ("contact", "email"),
    ):
        if (
            not review.get(key + "_source")
            or not str(review.get(key + "_note", "")).strip()
        ):
            blockers.append(f"Record {label} source and evidence")
    return blockers


def review_lead(record_id, payload):
    payload = dict(payload)
    if payload.get("email"):
        payload["email"] = normalize_email(payload["email"])
    for key in ("identity_source", "website_source", "contact_source"):
        if payload.get(key):
            payload[key] = public_url(payload[key])
    if payload.get("website_url"):
        payload["website_url"] = public_url(payload["website_url"])
    if payload.get("website_url") and payload.get("website_status") != "found":
        raise ValueError(
            "A recorded independent website conflicts with a no-website finding; choose Website found or clear the URL with evidence"
        )
    if payload.get("website_status") == "found" and not payload.get("website_url"):
        raise ValueError("Record the website URL when a website is found")
    blockers = review_blockers(payload)
    if payload.get("decision") == "qualified" and blockers:
        raise ValueError("; ".join(blockers))
    if (
        payload.get("decision") == "rejected"
        and not payload.get("decision_note", "").strip()
    ):
        raise ValueError("Record why the lead is rejected")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT data FROM records WHERE kind='leads' AND id=?", (record_id,)
        ).fetchone()
        if not row:
            raise KeyError(record_id)
        lead = json.loads(row[0])
        if (
            lead.get("source") == "tavily"
            and payload.get("decision") == "qualified"
            and not payload.get("confirmed_name", "").strip()
        ):
            raise ValueError(
                "Confirm the exact business and branch name; a web search title is not a verified business name"
            )
        if lead.get("revision", 0) != payload.pop("revision"):
            raise ConflictError("Lead changed; reload it before saving your review")
        payload["reviewed_at"] = now()
        lead.update(
            review=payload,
            review_invalidated=False,
            status=payload["decision"],
            requires_review=payload["decision"] == "needs_review",
            revision=lead.get("revision", 0) + 1,
            updated_at=now(),
        )
        if payload.get("confirmed_name", "").strip():
            lead["name"] = payload["confirmed_name"].strip()
        db.execute(
            "UPDATE records SET data=? WHERE kind='leads' AND id=?",
            (json.dumps(lead), record_id),
        )
        db.execute(
            "INSERT INTO records VALUES ('lead_reviews', ?, ?)",
            (uuid4().hex, json.dumps({"lead_id": record_id, **payload})),
        )
        # Verification is separate from permission. Preserve consent and suppression exactly.
        if (
            payload.get("contact_verified")
            and payload.get("email")
            and payload.get("contact_source")
            and payload.get("contact_note", "").strip()
        ):
            email = payload["email"]
            row = db.execute(
                "SELECT data FROM records WHERE kind='contacts' AND id=?", (email,)
            ).fetchone()
            contact = (
                json.loads(row[0])
                if row
                else {
                    "id": email,
                    "email": email,
                    "consent": "unknown",
                    "created_at": now(),
                }
            )
            contact.update(
                verified=True,
                verification_source=payload["contact_source"],
                verification_evidence=payload["contact_note"],
                verification_lead_id=record_id,
                updated_at=now(),
            )
            db.execute(
                "INSERT INTO records VALUES ('contacts', ?, ?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                (email, json.dumps(contact)),
            )
        db.execute(
            "INSERT INTO activity VALUES (?, ?, ?, ?, ?)",
            (
                uuid4().hex,
                "leads.reviewed",
                record_id,
                now(),
                json.dumps({"decision": lead["status"]}),
            ),
        )
    return lead


def ensure_qualified(record_id, recipient=None, *, require_consent=True):
    lead = store.get("leads", record_id)
    if not lead:
        raise EligibilityError("Reviewed lead not found")
    review = lead.get("review") or {}
    if (
        lead.get("status") != "qualified"
        or lead.get("review_invalidated")
        or review_blockers(review)
        or (
            lead.get("source") == "tavily"
            and not review.get("confirmed_name", "").strip()
        )
    ):
        raise EligibilityError(
            "Lead needs a complete identity, activity, website and contact review"
        )
    try:
        reviewed_at = datetime.fromisoformat(review["reviewed_at"])
        age = datetime.now(timezone.utc) - reviewed_at
        if age > MAX_EVIDENCE_AGE or age < timedelta(minutes=-5):
            raise ValueError("stale")
    except (KeyError, ValueError, TypeError):
        raise EligibilityError(
            "Lead evidence is over 30 days old or invalid; review it again"
        )
    inspection = store.get("lead_inspections", record_id)
    if (
        inspection
        and inspection.get("fingerprint") == observation_fingerprint(lead)
        and inspection["checked_at"] > review["reviewed_at"]
    ):
        raise EligibilityError(
            "New source inspection findings need review before outreach; review the findings and save the evidence again"
        )
    if recipient and normalize_email(recipient) != review["email"]:
        raise EligibilityError("Draft recipient no longer matches the reviewed lead")
    if require_consent:
        ensure_eligible(review["email"], "outreach")
    return lead


def lead_view(lead):
    lead = dict(lead)
    review = lead.get("review") or {}
    lead["blockers"] = review_blockers(review)
    lead["source_freshness"] = source_freshness(lead.get("observation") or {})
    inspection = store.get("lead_inspections", lead["id"])
    if inspection:
        inspection = normalize_inspection(inspection)
    lead["source_inspection"] = (
        {
            **inspection,
            "stale": inspection.get("fingerprint") != observation_fingerprint(lead)
            or inspection.get("expires", 0) <= time.time(),
        }
        if inspection
        else None
    )
    try:
        ensure_qualified(lead["id"])
        lead["ready_to_draft"] = True
        lead["dispatch_blocker"] = ""
    except EligibilityError as exc:
        lead["ready_to_draft"] = False
        lead["dispatch_blocker"] = str(exc)
    lead["consent"] = (store.get("contacts", review.get("email", "")) or {}).get(
        "consent", "unknown"
    )
    lead["possible_duplicates"] = [
        p["id"]
        for p in store.list("leads")
        if p["id"] != lead["id"]
        and normalized(p.get("name", "")) == normalized(lead.get("name", ""))
        and normalized(p.get("location", "")) == normalized(lead.get("location", ""))
    ]
    return lead


def initial_outreach_state(lead, mailbox):
    """Read-only duplicate/history checks shared by queueing and dry runs."""
    if not mailbox:
        raise EligibilityError("Connect Gmail before creating outreach drafts")
    email = lead["review"]["email"]
    # One initial outreach per mailbox/contact. Repeat discovery cannot queue duplicate sends.
    key = "outreach_" + hashlib.sha256(f"{mailbox}:{email}".encode()).hexdigest()[:24]
    existing = store.get("approvals", key)
    if existing:
        return key, existing
    prior_submissions = [
        m
        for m in store.list("messages")
        if m.get("from") == mailbox
        and m.get("to") == email
        and m.get("purpose") == "outreach"
        and m.get("status") in ("sending", "delivery_unknown", "sent")
    ]
    prior_drafts = [
        a
        for a in store.list("approvals")
        if a.get("recipient_email") == email
        and a.get("sender_mailbox") in (None, mailbox)
        and a.get("purpose") == "outreach"
        and a.get("status") not in ("rejected", "failed")
    ]
    if prior_submissions or prior_drafts:
        raise EligibilityError(
            "Initial outreach already exists for this mailbox/contact; review its history instead of creating a duplicate"
        )
    return key, None


def draft_lead(
    record_id, subject, body, mailbox, proposal_preview_id=None, campaign_source=None
):
    if not subject.strip() or not body.strip() or "\r" in subject or "\n" in subject:
        raise ValueError("Provide a non-empty message and a single-line subject")
    if not mailbox:
        raise EligibilityError("Connect Gmail before creating outreach drafts")
    lead = ensure_qualified(record_id)
    email = lead["review"]["email"]
    snapshot = None
    if proposal_preview_id:
        from services.proposals import preview_snapshot

        snapshot = preview_snapshot(proposal_preview_id, lead, mailbox, subject, body)
    from agents.human_approval import queue_approval

    key, existing = initial_outreach_state(lead, mailbox)
    if existing:
        return existing
    return queue_approval(
        key,
        {
            "recipient_email": email,
            "sender_mailbox": mailbox,
            "subject": subject,
            "draft_response": body,
            "intent": "sales",
            "purpose": "outreach",
            "lead_id": record_id,
            "lead_revision": lead["revision"],
            "client_name": lead["name"],
            "lead_data": {"id": record_id, "name": lead["name"]},
            **({"proposal_snapshot": snapshot} if snapshot else {}),
            **({"campaign_source": campaign_source} if campaign_source else {}),
        },
    )
