"""Bounded follow-up drafts: real-ledger fixtures, fake Gmail, no live outreach."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from config import settings
from core.store import store, ConflictError
from services.contacts import EligibilityError, suppress
from services.email_service import email_service
from services.lead_service import draft_lead, review_lead
from services import followups
from services.proposals import Portfolio, portfolio, save_portfolio
from services.report_service import build_report
from agents.human_approval import approve_draft
from test_leads_phase4 import qualified, review_payload
from test_foundation import gmail_client


def raw_record(kind, record_id, data):
    with store.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO records VALUES (?, ?, ?)",
            (kind, record_id, json.dumps({**data, "id": record_id})),
        )
    return store.get(kind, record_id)


def original(**changes):
    lead = qualified()
    approval = draft_lead(
        lead["id"],
        "Website proposal",
        "Original proposal",
        email_service.expected_email,
    )
    store.put(
        "approvals",
        approval["id"],
        {**approval, "status": "sent", "provider_thread_id": "thread-1"},
    )
    message = raw_record(
        "messages",
        "initial",
        {
            "from": email_service.expected_email,
            "to": "owner@example.test",
            "purpose": "outreach",
            "status": "sent",
            "provider_message_id": "original-provider",
            "thread_id": "thread-1",
            "rfc_message_id": "<original@example.test>",
            "subject": "Website proposal",
            "body": "Original proposal",
            "approval_id": approval["id"],
            "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
            **changes,
        },
    )
    store.put(
        "gmail_cursor",
        email_service.expected_email,
        {"history_id": "100", "thread_ids": ["thread-1"]},
    )
    return message, lead


def prepare():
    message, lead = original()
    preview = followups.preview(message["id"], email_service.expected_email)
    draft = followups.queue(
        message["id"],
        email_service.expected_email,
        preview["id"],
        "Exact reviewed follow-up",
    )
    return message, lead, draft


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


def test_eligible_preview_is_local_threaded_and_not_sent_or_queued():
    message, lead = original()
    preview = followups.preview(message["id"], email_service.expected_email)
    assert preview["subject"] == "Re: Website proposal"
    assert (
        lead["name"] in preview["body"]
        and "https://ts-industries.co.za/" in preview["body"]
    )
    assert (
        "unsubscribe" in preview["body"] and "pharezsigasa@gmail.com" in preview["body"]
    )
    assert len(store.list("approvals")) == 1  # Initial, already-sent approval only.
    assert len(store.list("messages")) == 1
    assert followups.list_candidates(email_service.expected_email)["candidates"][0][
        "eligible"
    ]


def test_exact_seven_day_boundary_uses_elapsed_time():
    message, _ = original()
    due = datetime.fromisoformat(message["created_at"]) + timedelta(days=7)
    raw_record(
        "gmail_cursor",
        email_service.expected_email,
        {
            "updated_at": (due - timedelta(minutes=1)).isoformat(),
            "thread_ids": [message["thread_id"]],
        },
    )
    with pytest.raises(EligibilityError, match="7 days"):
        followups.context(
            message["id"],
            email_service.expected_email,
            at=due - timedelta(microseconds=1),
        )
    assert (
        followups.context(message["id"], email_service.expected_email, at=due)[0]["id"]
        == message["id"]
    )


@pytest.mark.parametrize(
    "change",
    [
        {"purpose": "test"},
        {"status": "sending"},
        {"provider_message_id": ""},
        {"thread_id": ""},
        {"rfc_message_id": ""},
        {"followup_of": "earlier"},
    ],
)
def test_unconfirmed_legacy_test_or_followup_sources_cannot_generate(change):
    message, _ = original(**change)
    with pytest.raises(EligibilityError):
        followups.preview(message["id"], email_service.expected_email)


@pytest.mark.parametrize("cursor_time", ["missing", "stale", "future"])
def test_sync_is_required_and_must_be_recent(cursor_time):
    message, _ = original()
    if cursor_time == "missing":
        store.delete("gmail_cursor", email_service.expected_email)
    else:
        when = datetime.now(timezone.utc) + (
            timedelta(minutes=1) if cursor_time == "future" else -timedelta(minutes=16)
        )
        raw_record(
            "gmail_cursor",
            email_service.expected_email,
            {"updated_at": when.isoformat()},
        )
    with pytest.raises(EligibilityError, match="Sync Gmail"):
        followups.preview(message["id"], email_service.expected_email)


def test_recent_cursor_that_did_not_include_this_thread_is_insufficient():
    message, _ = original()
    store.put(
        "gmail_cursor",
        email_service.expected_email,
        {"history_id": "100", "thread_ids": []},
    )
    with pytest.raises(EligibilityError, match="Sync Gmail"):
        followups.preview(message["id"], email_service.expected_email)


@pytest.mark.parametrize(
    "flags", [{}, {"automated": True}, {"bounce": True}, {"unsubscribe": True}]
)
def test_any_incoming_notice_blocks_no_response_followup(flags):
    message, _ = original()
    store.put(
        "inbox",
        "reply",
        {
            "mailbox": email_service.expected_email,
            "thread_id": message["thread_id"],
            "sender": message["to"],
            **flags,
        },
    )
    with pytest.raises(EligibilityError, match="reply, automated notice or bounce"):
        followups.preview(message["id"], email_service.expected_email)


@pytest.mark.parametrize("outcome", ["interested", "declined", "won", "unsubscribed"])
def test_explicit_outcomes_block_followup(outcome):
    message, _ = original()
    store.record_outcome(
        email_service.expected_email,
        message["thread_id"],
        message["to"],
        outcome,
        "Operator evidence",
    )
    with pytest.raises(EligibilityError, match="explicit outcome"):
        followups.preview(message["id"], email_service.expected_email)


def test_contact_suppression_changed_review_and_missing_lead_block_followups():
    message, lead = original()
    suppress(message["to"], "Stop")
    with pytest.raises(EligibilityError):
        followups.preview(message["id"], email_service.expected_email)
    # An unlinked initial message cannot acquire qualification from its email address.
    store.put("messages", message["id"], {**message, "approval_id": None})
    with pytest.raises(EligibilityError, match="no linked"):
        followups.preview(message["id"], email_service.expected_email)
    store.put("messages", message["id"], message)
    review_lead(
        lead["id"],
        review_payload(
            lead,
            decision="rejected",
            decision_note="Business already has a website",
            website_status="found",
            website_url="https://business.example.test/",
        ),
    )
    with pytest.raises(EligibilityError):
        followups.preview(message["id"], email_service.expected_email)


@pytest.mark.parametrize("status", ["sending", "delivery_unknown"])
def test_uncertain_dispatch_blocks_followup(status):
    message, _ = original()
    store.put(
        "messages",
        "uncertain",
        {
            "from": email_service.expected_email,
            "thread_id": message["thread_id"],
            "status": status,
        },
    )
    with pytest.raises(EligibilityError, match="uncertain"):
        followups.preview(message["id"], email_service.expected_email)


def test_another_pending_draft_blocks_followup():
    message, _ = original()
    store.queue_approval(
        "reply-pending",
        {
            "sender_mailbox": email_service.expected_email,
            "provider_thread_id": message["thread_id"],
        },
    )
    with pytest.raises(EligibilityError, match="Another draft"):
        followups.preview(message["id"], email_service.expected_email)


def test_additional_sent_message_blocks_no_response_followup():
    message, _ = original()
    store.put(
        "messages",
        "manual-response",
        {
            "from": email_service.expected_email,
            "thread_id": message["thread_id"],
            "status": "sent",
            "purpose": "reply",
        },
    )
    with pytest.raises(EligibilityError, match="Another message"):
        followups.preview(message["id"], email_service.expected_email)


@pytest.mark.asyncio
async def test_stale_sync_after_queue_blocks_approval(monkeypatch):
    _, _, draft = prepare()
    raw_record(
        "gmail_cursor",
        email_service.expected_email,
        {
            "updated_at": (
                datetime.now(timezone.utc) - timedelta(minutes=16)
            ).isoformat()
        },
    )
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EligibilityError, match="Sync Gmail"):
        await approve_draft(draft["id"])
    assert messages.send.call_count == 0


@pytest.mark.parametrize("change", ["source", "lead", "portfolio"])
def test_changed_source_review_or_catalog_invalidates_preview(change):
    message, lead = original()
    preview = followups.preview(message["id"], email_service.expected_email)
    if change == "source":
        store.put("messages", message["id"], {**message, "subject": "Changed"})
    elif change == "lead":
        review_lead(lead["id"], review_payload(lead))
    else:
        save_portfolio(Portfolio(**portfolio()))
    with pytest.raises(ConflictError):
        followups.queue(
            message["id"], email_service.expected_email, preview["id"], "Follow up"
        )


def test_concurrent_queue_requests_cannot_create_two_followups():
    message, _ = original()
    preview = followups.preview(message["id"], email_service.expected_email)

    def create(index):
        try:
            return followups.queue(
                message["id"],
                email_service.expected_email,
                preview["id"],
                f"Message {index}",
            )
        except EligibilityError:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(create, range(4)))
    drafts = [d for d in store.list("approvals") if d.get("followup_of")]
    assert len(drafts) == 1
    assert all(v["id"] == drafts[0]["id"] for v in values if v)
    assert all(v["draft_response"] == drafts[0]["draft_response"] for v in values if v)


@pytest.mark.asyncio
async def test_reviewed_followup_sends_exact_text_once_and_reports_one_conversation(
    monkeypatch,
):
    message, _, draft = prepare()
    client, messages = gmail_client(
        message={"id": "followup-provider", "threadId": message["thread_id"]}
    )
    monkeypatch.setattr(email_service, "client", client)
    assert messages.send.call_count == 0
    await approve_draft(draft["id"])
    await approve_draft(draft["id"])
    assert messages.send.call_count == 1
    payload = messages.send.call_args.kwargs["body"]
    assert payload["threadId"] == message["thread_id"]
    mime = message_from_bytes(base64.urlsafe_b64decode(payload["raw"]))
    assert mime["In-Reply-To"] == message["rfc_message_id"]
    assert mime.get_payload(decode=True).decode() == "Exact reviewed follow-up"
    sent = [m for m in store.list("messages") if m.get("followup_of")]
    assert len(sent) == 1 and sent[0]["status"] == "sent"
    today = (
        datetime.now(timezone.utc).astimezone(ZoneInfo("Africa/Johannesburg")).date()
    )
    report = build_report(
        today - timedelta(days=10), today, mailbox=email_service.expected_email
    )
    assert report["summary"]["emails_sent"] == 2
    assert report["summary"]["conversations_sent"] == 1
    with pytest.raises(EligibilityError, match="already exists"):
        followups.preview(message["id"], email_service.expected_email)


@pytest.mark.asyncio
async def test_reply_after_queue_blocks_approval(monkeypatch):
    message, _, draft = prepare()
    store.put(
        "inbox",
        "reply",
        {"mailbox": email_service.expected_email, "thread_id": message["thread_id"]},
    )
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EligibilityError, match="reply"):
        await approve_draft(draft["id"])
    assert messages.send.call_count == 0


@pytest.mark.asyncio
async def test_reply_arriving_during_provider_preflight_blocks_submission(monkeypatch):
    message, _, draft = prepare()
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    original_profile = email_service.get_profile

    async def changed():
        profile = await original_profile()
        store.put(
            "inbox",
            "reply",
            {
                "mailbox": email_service.expected_email,
                "thread_id": message["thread_id"],
            },
        )
        return profile

    monkeypatch.setattr(email_service, "get_profile", changed)
    with pytest.raises(EligibilityError):
        await approve_draft(draft["id"])
    assert messages.send.call_count == 0
    assert store.get("approvals", draft["id"])["status"] == "failed"


def test_followup_routes_require_auth_and_scope_mailbox(api, monkeypatch):
    message, _ = original()
    path = f"/api/followups/{message['id']}"
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.get("/api/followups").status_code == 401
    assert api.post(path + "/preview").status_code == 401
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    assert api.get("/api/followups").json()["automatic_sending"] is False
    preview = api.post(path + "/preview").json()
    assert (
        api.post(
            path + "/draft",
            json={
                "preview_id": preview["id"],
                "body": "Edited follow-up",
                "recipient": "wrong@example.test",
            },
        ).status_code
        == 422
    )
    result = api.post(
        path + "/draft", json={"preview_id": preview["id"], "body": "Edited follow-up"}
    )
    assert (
        result.status_code == 200 and result.json()["recipient_email"] == message["to"]
    )
    monkeypatch.setattr(email_service, "expected_email", "different@example.test")
    assert api.get("/api/followups").json()["candidates"] == []
    assert api.post(path + "/preview").status_code == 404
