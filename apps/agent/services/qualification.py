"""Conservative two-source qualification using explicit listing fields, never an LLM."""

import hashlib
import json
import re
import time
from datetime import date, datetime
from urllib.parse import urlsplit

from core.store import store, now, ConflictError
from services.contacts import normalize_email, EligibilityError
from services.lead_service import public_url, observation_fingerprint, review_lead
from services.report_service import TZ
from services.web_research import reserve_request, request_search, request_provider

POLICY = 1
# Separate supported source domains; this is not a guarantee of independent ownership.
DIRECTORIES = (
    "brabys.com",
    "yellowpages.co.za",
    "cylex.net.za",
    "snupit.co.za",
    "hotfrog.co.za",
    "sayellow.com",
)
SOCIAL = ("facebook.com", "instagram.com", "linkedin.com")
FIELDS = (
    "business name",
    "town",
    "address",
    "phone",
    "email",
    "business status",
    "activity verified",
    "website",
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def canonical(url, domains=DIRECTORIES):
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return next((d for d in domains if host == d or host.endswith("." + d)), None)


def normalized(value):
    return " ".join(re.findall(r"\w+", value.casefold()))


def listing_fields(text):
    """Accept explicit single-value labels only. Dates elsewhere are not activity proof."""
    values, snippets = {}, {}
    for raw in text.splitlines():
        line = raw.strip().replace("**", "")
        match = re.fullmatch(r"([A-Za-z ]{3,30}):\s*(.{1,250})", line)
        if not match:
            continue
        label, value = match.group(1).casefold(), match.group(2).strip()
        if label not in FIELDS:
            continue
        if label in values:
            raise ValueError("Repeated business fields make source ownership ambiguous")
        values[label], snippets[label] = value, raw.strip()[:300]
    if set(values) != set(FIELDS):
        raise ValueError(
            "Source lacks explicit business identity, branch, contact, activity-verification or website fields"
        )
    digits = re.sub(r"\D", "", values["phone"])
    if len(digits) == 10 and digits.startswith("0"):
        digits = "27" + digits[1:]
    if len(digits) != 11 or not digits.startswith("27"):
        raise ValueError("Source phone is not one South African number")
    values["phone"] = "+" + digits
    values["email"] = normalize_email(values["email"])
    if not re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,24}", values["email"]):
        raise ValueError("Source email is not one literal address")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", values["activity verified"]):
        raise ValueError("Activity verification needs an explicit YYYY-MM-DD date")
    verified = date.fromisoformat(values["activity verified"])
    if not 0 <= (datetime.now(TZ).date() - verified).days <= 30:
        raise ValueError("Explicit activity verification is stale or future-dated")
    if (
        len(normalized(values["business name"])) < 5
        or len(normalized(values["address"])) < 8
    ):
        raise ValueError("Business name or branch address is insufficient")
    return {
        "values": values,
        "snippets": snippets,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
    }


def primary(lead):
    inspection = store.get("lead_inspections", lead["id"]) or {}
    if (
        not canonical(lead["source_url"])
        or inspection.get("fingerprint") != observation_fingerprint(lead)
        or inspection.get("expires", 0) <= time.time()
        or not inspection.get("qualification_fields")
    ):
        raise ValueError("No fresh supported structured source inspection")
    fields = inspection["qualification_fields"]
    if fields.get("error"):
        raise ValueError(fields["error"])
    values = fields["values"]
    if normalized(values["town"]) != normalized(lead["location"]):
        raise ValueError("Source town does not match the target town")
    if normalized(values["business name"]) not in normalized(lead["name"]):
        raise ValueError("Source business name does not match the saved candidate")
    if lead.get("email") and normalize_email(lead["email"]) != values["email"]:
        raise ValueError("Source email conflicts with the saved candidate")
    if lead.get("address") and normalized(lead["address"]) not in normalized(
        values["address"]
    ):
        raise ValueError("Source address conflicts with the saved branch")
    if lead.get("phone"):
        digits = re.sub(r"\D", "", lead["phone"])
        if len(digits) == 10 and digits.startswith("0"):
            digits = "27" + digits[1:]
        if "+" + digits != values["phone"]:
            raise ValueError("Source phone conflicts with the saved candidate")
    return inspection


def result(lead, decision, reason, **extra):
    value = {
        "lead_id": lead["id"],
        "decision": decision,
        "reason": reason,
        "policy_version": POLICY,
        "assessed_at": now(),
        **extra,
    }
    store.put("lead_qualification", lead["id"], value)
    return value


def start(lead, remaining_requests):
    if lead.get("review") and lead["review"].get("origin") != "automation":
        return result(
            lead, "operator_review", "Existing operator decision is preserved"
        )
    try:
        primary(lead)
    except ValueError as exc:
        return result(lead, "needs_review", str(exc))
    if remaining_requests < 2:
        return result(
            lead,
            "needs_review",
            "Qualification needs up to two additional requests within this job's budget",
        )
    return {"next_stage": "qualify_search"}


async def advance(lead, stage):
    if lead.get("review") and lead["review"].get("origin") != "automation":
        return result(
            lead,
            "operator_review",
            "Operator decision changed during qualification and is preserved",
        )
    try:
        first = primary(lead)
    except ValueError as exc:
        return result(lead, "needs_review", str(exc))
    fingerprint = digest(
        {"inspection": first, "observation": observation_fingerprint(lead)}
    )
    if stage == "qualify_search":
        values = first["qualification_fields"]["values"]
        terms = [
            values["business name"],
            values["town"],
            values["phone"],
            values["email"].split("@")[1],
        ]
        query = (
            " ".join('"' + term.replace('"', "") + '"' for term in terms)
            + " official website"
        )
        reserve_request()
        response = await request_search(query, 5)
        hits = response["results"]
        if not hits or len(hits) >= 5:
            return result(
                lead,
                "needs_review",
                "Website search is empty or capped; absence is unresolved",
            )
        urls = []
        try:
            for hit in hits:
                url = public_url(hit.get("url", ""))
                if not canonical(url, DIRECTORIES + SOCIAL):
                    return result(
                        lead,
                        "needs_review",
                        "Search found a possible independent website or unsupported source",
                        possible_website=url,
                    )
                urls.append(url)
        except (ValueError, AttributeError):
            return result(
                lead,
                "needs_review",
                "Search contains invalid or incomplete source URLs",
            )
        second = next(
            (
                u
                for u in urls
                if canonical(u) and canonical(u) != canonical(lead["source_url"])
            ),
            None,
        )
        if not second:
            return result(
                lead,
                "needs_review",
                "No corroborating source on another supported directory domain",
            )
        store.put(
            "qualification_work",
            lead["id"],
            {
                "fingerprint": fingerprint,
                "source_url": second,
                "search": {"query": query, "urls": urls, "checked_at": now()},
            },
        )
        return {"next_stage": "qualify_extract"}
    work = store.get("qualification_work", lead["id"]) or {}
    if work.get("fingerprint") != fingerprint:
        raise ConflictError("Primary source changed during automatic qualification")
    reserve_request()
    response = await request_provider(
        "extract",
        {
            "urls": [work["source_url"]],
            "extract_depth": "basic",
            "format": "markdown",
            "include_images": False,
            "include_favicon": False,
            "timeout": 15,
        },
    )
    hits = response["results"]
    if (
        response.get("failed_results")
        or len(hits) != 1
        or hits[0].get("url") != work["source_url"]
    ):
        return result(
            lead, "needs_review", "Corroborating source failed or changed URL"
        )
    text = hits[0].get("raw_content")
    if not isinstance(text, str) or not text.strip() or len(text) > 200_000:
        return result(
            lead, "needs_review", "Corroborating source content is empty or oversized"
        )
    try:
        second = listing_fields(text)
        return publish(lead, first, work, second)
    except ValueError as exc:
        return result(lead, "needs_review", str(exc))


def publish(lead, first, work, second):
    a, b = first["qualification_fields"]["values"], second["values"]
    for key in ("business name", "town", "address", "phone", "email"):
        if (
            a[key] != b[key]
            if key in ("email", "phone")
            else normalized(a[key]) != normalized(b[key])
        ):
            raise ValueError(
                f"Sources disagree about {key}; branch ownership is unresolved"
            )
    if first["qualification_fields"]["text_hash"] == second["text_hash"]:
        raise ValueError("Identical source copies are not sufficient corroboration")
    statuses = {a["business status"].casefold(), b["business status"].casefold()}
    if statuses & {"closed", "permanently closed", "ceased trading", "inactive"}:
        return result(
            lead,
            "excluded",
            "A matched source explicitly reports the business closed/inactive",
        )
    if not statuses <= {"active", "operational", "open"}:
        raise ValueError("Sources do not explicitly agree that the business operates")
    websites = {a["website"].casefold(), b["website"].casefold()}
    if not websites <= {"none", "no website", "not listed"}:
        try:
            if public_url(a["website"]) == public_url(b["website"]):
                return result(
                    lead,
                    "excluded",
                    "Both matched listings link a website; not a no-website target",
                )
        except ValueError:
            pass
        raise ValueError("Website fields conflict or are uncertain")
    evidence = {
        "policy_version": POLICY,
        "lead_id": lead["id"],
        "observation_fingerprint": observation_fingerprint(lead),
        "primary_inspection_hash": digest(first),
        "sources": [
            {"url": first["source_url"], **first["qualification_fields"]},
            {"url": work["source_url"], **second},
        ],
        "website_search": work["search"],
        "checked_at": now(),
        "expires": min(first["expires"], time.time() + 86400),
        "limitations": "Source assertions and a bounded search, not a guarantee of current activity or website absence. Recipient permission is checked separately.",
    }
    evidence_id = digest(evidence)
    store.insert_once("qualification_evidence", evidence_id, evidence)
    reviewed = review_lead(
        lead["id"],
        {
            "revision": lead.get("revision", 0),
            "origin": "automation",
            "qualification_evidence_id": evidence_id,
            "confirmed_name": a["business name"],
            "identity_verified": True,
            "business_status": "active",
            "identity_source": first["source_url"],
            "identity_note": "Automated match of explicit name/town/address/phone/email across two supported directory domains",
            "activity_method": "recent_public_activity",
            "activity_date": min(a["activity verified"], b["activity verified"]),
            "website_status": "not_found_after_review",
            "website_source": work["source_url"],
            "website_note": "Both matched listings explicitly have no listed website; bounded exact-business search returned only supported listing/social domains. Absence is not guaranteed.",
            "contact_verified": True,
            "email": a["email"],
            "contact_source": work["source_url"],
            "contact_note": "Exact email matches both explicit business/branch records; no consent inferred",
            "decision": "qualified",
            "decision_note": "Automatic qualification policy 1; see immutable source snapshot",
        },
    )
    return result(
        reviewed,
        "qualified",
        "Two-source automated checks passed; contact permission and sending approval remain separate",
        evidence_id=evidence_id,
    )


def validate(lead):
    review = lead.get("review") or {}
    decision = store.get("lead_qualification", lead["id"]) or {}
    if review.get("origin") != "automation":
        return
    evidence = (
        store.get("qualification_evidence", review.get("qualification_evidence_id", ""))
        or {}
    )
    inspection = store.get("lead_inspections", lead["id"]) or {}
    if (
        evidence.get("policy_version") != POLICY
        or evidence.get("expires", 0) <= time.time()
        or evidence.get("lead_id") != lead["id"]
        or evidence.get("observation_fingerprint") != observation_fingerprint(lead)
        or evidence.get("primary_inspection_hash") != digest(inspection)
        or decision.get("decision") != "qualified"
        or decision.get("evidence_id") != review.get("qualification_evidence_id")
    ):
        raise EligibilityError(
            "Automatic qualification evidence expired or changed; a new supported qualification is required"
        )
    if review.get("email") != evidence["sources"][0]["values"]["email"]:
        raise EligibilityError(
            "Automatic qualification email no longer matches its evidence"
        )
