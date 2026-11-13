"""Approval-controlled ElevenLabs SIP pilot. Never retry an uncertain call."""

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo
from config import settings
from core.store import store, now, ConflictError
from services import automation, elevenlabs, spend
from services.email_service import email_service
from services.lead_service import ensure_qualified

ACTIVE = ("sending", "delivery_unknown", "initiated", "in-progress", "processing")
DISCLOSURE = "Hello, I'm the AI assistant calling on behalf of TS Industries about website services. Is now a suitable time?"


def phone(value):
    value = re.sub(r"[\s()-]", "", value or "")
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise ValueError(
            "Record an international phone number beginning with + and its country code; local numbers are not guessed"
        )
    return value


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def redact(record):
    return {k: v for k, v in record.items() if k != "token_hash"}


def setup():
    blockers = []
    for name in (
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_AGENT_ID",
        "ELEVENLABS_PHONE_NUMBER_ID",
        "OPENAI_API_KEY",
        "ELEVENLABS_LLM_URL",
    ):
        if not getattr(settings, name):
            blockers.append(f"Configure {name} locally")
    if len(settings.ELEVENLABS_LLM_SECRET) < 32:
        blockers.append(
            "Configure a dedicated ELEVENLABS_LLM_SECRET of at least 32 characters"
        )
    if not settings.ELEVENLABS_CALLS_ENABLED:
        blockers.append("Phone calls are disabled in backend configuration")
    return {
        "blockers": blockers,
        "enabled": not blockers,
        "warning": "A normal SIM number alone cannot dial through this API. Connect an authorized SIP trunk in ElevenLabs. Provider caps are required in addition to local estimates.",
    }


def context_for(lead):
    previous = [
        c
        for c in store.list("phone_calls")
        if c.get("lead_id") == lead["id"] and c.get("status") == "done"
    ]
    return {
        "business": lead.get("confirmed_name") or lead.get("name"),
        "location": lead.get("location"),
        "portfolio": "https://ts-industries.co.za; projects: https://rbptech.co.za and https://rhymamusic.co.za",
        "previous_calls": [
            {
                "summary": c.get("summary", ""),
                "transcript": c.get("transcript", [])[-6:],
            }
            for c in previous[-2:]
        ],
    }


def eligible(lead_id):
    lead = ensure_qualified(lead_id)
    number = phone(lead.get("phone"))
    if store.get("phone_suppression", number):
        raise ValueError("This phone number is on the do-not-call list")
    saved = automation.config(email_service.expected_email)
    if not saved.get("target_month") or not saved.get("country"):
        raise ValueError("Save a monthly town/country target before preparing calls")
    if lead.get("location", "").casefold() != automation.target_label(saved).casefold():
        raise ValueError("This business is outside the selected town target")
    return lead, number, saved


def prepare(lead_id, permission_evidence):
    if not permission_evidence.strip():
        raise ValueError(
            "Record actual permission for an AI phone call, separately from email permission"
        )
    lead, number, target = eligible(lead_id)
    key = digest(
        [email_service.expected_email, lead_id, number, target["target_month"]]
    )
    value = {
        "lead_id": lead_id,
        "name": lead.get("name"),
        "number": number,
        "mailbox": email_service.expected_email,
        "permission_evidence": permission_evidence,
        "lead_fingerprint": digest(lead),
        "target_fingerprint": target_digest(target),
        "target_month": target["target_month"],
        "status": "awaiting_approval",
        "opening": DISCLOSURE,
        "context": context_for(lead),
        "max_seconds": settings.CALL_MAX_SECONDS,
    }
    return redact(store.insert_once("phone_calls", key, value))


def target_digest(target):
    return digest(
        {
            k: target.get(k)
            for k in ("location", "region", "country", "target_month", "time_zone")
        }
    )


def owned(call_id):
    record = store.get("phone_calls", call_id)
    if not record or record.get("mailbox") != email_service.expected_email:
        raise ValueError("Call record unavailable in the connected mailbox")
    return record


async def dispatch(call_id):
    record = owned(call_id)
    if record["status"] != "awaiting_approval":
        raise ConflictError(
            "This call was already claimed or held; no automatic redial"
        )
    if setup()["blockers"]:
        raise ValueError("; ".join(setup()["blockers"]))
    lead, number, target = eligible(record["lead_id"])
    if (
        digest(lead) != record["lead_fingerprint"]
        or target_digest(target) != record["target_fingerprint"]
    ):
        raise ValueError(
            "Business evidence or target changed; reject this saved call and review again"
        )
    local = datetime.now(timezone.utc).astimezone(ZoneInfo(target["time_zone"]))
    if (
        local.strftime("%Y-%m") != target["target_month"]
        or local.weekday() > 4
        or not 9 <= local.hour < 17
    ):
        raise ValueError(
            "Calls are limited to weekdays, 09:00–17:00 in the selected town's time zone and month"
        )
    owner = uuid4().hex
    store.acquire_lease("phone-dispatch", owner)
    try:
        record = owned(call_id)
        if record["status"] != "awaiting_approval" or any(
            c.get("status") in ACTIVE for c in store.list("phone_calls")
        ):
            raise ConflictError(
                "Another call is active or uncertain; reconcile before dialing"
            )
        # The provider must use our restricted custom LLM, not the operator workflow.
        agent_id = elevenlabs.identifier(settings.ELEVENLABS_AGENT_ID)
        agent = json.loads(await elevenlabs.request("GET", f"convai/agents/{agent_id}"))
        custom = (
            agent.get("conversation_config", {})
            .get("agent", {})
            .get("prompt", {})
            .get("custom_llm")
            or {}
        )
        prompt_config = (
            agent.get("conversation_config", {}).get("agent", {}).get("prompt", {})
        )
        if prompt_config.get("llm") != "custom-llm":
            raise ValueError("Select Custom LLM for the dedicated phone agent")
        if (agent.get("workflow") or {}).get("nodes"):
            raise ValueError(
                "Agent workflows are not enabled in this restricted phone pilot"
            )
        if prompt_config.get("tool_ids") or any(
            t.get("type") != "system" or t.get("name") != "end_call"
            for t in prompt_config.get("tools", [])
        ):
            raise ValueError(
                "Use a dedicated phone agent with only the end_call system tool; external tools are disabled for this pilot"
            )
        phone_id = elevenlabs.identifier(settings.ELEVENLABS_PHONE_NUMBER_ID)
        if not settings.ELEVENLABS_LLM_URL.startswith("https://") or custom.get(
            "url", ""
        ).rstrip("/") != settings.ELEVENLABS_LLM_URL.rstrip("/"):
            raise ValueError(
                "Configure the ElevenLabs agent with this app's restricted Custom LLM endpoint"
            )
        # Recheck after provider configuration lookup, immediately before claiming the call.
        fresh_lead, _, fresh_target = eligible(record["lead_id"])
        if (
            digest(fresh_lead) != record["lead_fingerprint"]
            or target_digest(fresh_target) != record["target_fingerprint"]
        ):
            raise ValueError(
                "Business evidence or target changed while preparing dispatch"
            )
        spend.reserve("elevenlabs-phone", settings.CALL_RESERVE_PENCE)
        token = secrets.token_urlsafe(32)
        store.transition(
            "phone_calls",
            call_id,
            ["awaiting_approval"],
            "sending",
            token_hash=digest(token),
            started_at=now(),
        )
        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": phone_id,
            "to_number": number,
            "conversation_initiation_client_data": {
                "custom_llm_extra_body": {"call_id": call_id, "call_token": token},
                "conversation_config_override": {
                    "conversation": {"max_duration_seconds": record["max_seconds"]},
                    "agent": {"first_message": record["opening"]},
                },
            },
        }
        try:
            result = json.loads(
                await elevenlabs.request(
                    "POST", "convai/sip-trunk/outbound-call", json=payload
                )
            )
            if result.get("success") is not True or not result.get("conversation_id"):
                raise ValueError("Provider did not confirm call")
            conversation_id = elevenlabs.identifier(result["conversation_id"])
            value = store.transition(
                "phone_calls",
                call_id,
                ["sending"],
                "initiated",
                conversation_id=conversation_id,
            )
            return redact(value)
        except Exception as exc:
            store.transition("phone_calls", call_id, ["sending"], "delivery_unknown")
            raise RuntimeError(
                "Call acceptance is uncertain. Check ElevenLabs; do not redial automatically."
            ) from exc
    finally:
        store.release_lease("phone-dispatch", owner)


async def sync(call_id):
    owner = uuid4().hex
    store.acquire_lease("phone-sync:" + call_id, owner)
    try:
        return await _sync(call_id)
    finally:
        store.release_lease("phone-sync:" + call_id, owner)


async def _sync(call_id):
    record = owned(call_id)
    if record["status"] in ("done", "failed"):
        return redact(record)
    if not record.get("conversation_id"):
        raise ValueError(
            "No provider conversation ID was confirmed. Inspect the ElevenLabs call log; do not retry this call"
        )
    conversation_id = elevenlabs.identifier(record["conversation_id"])
    result = json.loads(
        await elevenlabs.request("GET", f"convai/conversations/{conversation_id}")
    )
    if (
        result.get("conversation_id") != conversation_id
        or result.get("agent_id") != settings.ELEVENLABS_AGENT_ID
    ):
        raise ValueError("Provider returned a mismatched conversation")
    status = result.get("status")
    if status not in ("initiated", "in-progress", "processing", "done", "failed"):
        raise ValueError("Unknown provider call state")
    transcript = [
        {"role": t.get("role"), "text": str(t.get("message") or "")[:4000]}
        for t in result.get("transcript", [])[-100:]
    ]
    # Incoming words remain call data. They never enter the owner workflow or learned instructions.
    for turn in transcript:
        if turn["role"] == "user" and opted_out(turn["text"]):
            suppress(record["number"], "Opt-out in recorded call")
    analysis = result.get("analysis") or {}
    value = store.put(
        "phone_calls",
        call_id,
        {
            **record,
            "status": status,
            "transcript": transcript,
            "summary": str(analysis.get("transcript_summary") or "")[:4000],
            "duration_seconds": result.get("metadata", {}).get("call_duration_secs"),
            "provider_cost_usd": result.get("metadata", {}).get("cost_fiat"),
        },
    )
    return redact(value)


def suppress(number, reason):
    return store.put("phone_suppression", phone(number), {"reason": reason})


def opted_out(text):
    return bool(
        re.search(
            r"\b(stop calling|do not call|don't call|remove (?:me|us)|not interested)\b",
            text,
            re.I,
        )
    )


def bridge_record(call_id, token):
    if not settings.ELEVENLABS_CALLS_ENABLED:
        raise ValueError("Phone calling has been disabled")
    record = store.get("phone_calls", call_id) or {}
    if not record.get("token_hash") or not hmac.compare_digest(
        record["token_hash"], digest(token)
    ):
        raise ValueError("Invalid call binding")
    if record.get("status") not in ACTIVE:
        raise ValueError("This call is no longer active")
    started = datetime.fromisoformat(record["started_at"])
    if (datetime.now(timezone.utc) - started).total_seconds() > record[
        "max_seconds"
    ] + 120:
        raise ValueError("Call binding expired")
    return record
