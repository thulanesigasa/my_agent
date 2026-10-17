"""Recorded contact eligibility checked again at dispatch time."""

import re
from core.store import store, now


class EligibilityError(ValueError):
    pass


def normalize_email(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[^\s@<>,;]+@[^\s@<>,;]+\.[^\s@<>,;]+", value.strip()
    ):
        raise ValueError("Enter one plain email address")
    return value.strip().lower()


def save_contact(
    email,
    *,
    name="",
    verified=False,
    consent="unknown",
    evidence="",
    test_recipient=False
):
    email = normalize_email(email)
    if consent not in ("unknown", "granted", "declined", "unsubscribed"):
        raise ValueError("Unsupported consent status")
    if (verified or consent == "granted" or test_recipient) and not evidence.strip():
        raise ValueError(
            "Record evidence for contact verification, consent or test-address ownership"
        )
    previous = store.get("contacts", email) or {}
    return store.put(
        "contacts",
        email,
        {
            **previous,
            "email": email,
            "name": name,
            "verified": verified,
            "consent": consent,
            "evidence": evidence,
            "test_recipient": test_recipient,
            "consent_recorded_at": now(),
        },
    )


def suppress(email, reason):
    email = normalize_email(email)
    previous = store.get("contacts", email) or {"email": email}
    return store.put(
        "contacts",
        email,
        {**previous, "consent": "unsubscribed", "suppression_reason": reason},
    )


def ensure_eligible(email, purpose):
    email = normalize_email(email)
    contact = store.get("contacts", email) or {}
    if contact.get("consent") in ("declined", "unsubscribed"):
        raise EligibilityError("This contact is on the do-not-contact list")
    if purpose == "test":
        if not contact.get("test_recipient"):
            raise EligibilityError(
                "Confirm that you control this test address before sending"
            )
    elif purpose in ("outreach", "reply"):
        if not contact.get("verified") or contact.get("consent") != "granted":
            raise EligibilityError(
                "A verified contact and recorded consent are required before dispatch"
            )
    else:
        raise EligibilityError("This approval has an unsupported sending purpose")
    return contact
