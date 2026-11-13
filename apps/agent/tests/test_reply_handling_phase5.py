"""Reply suggestions, source-bound drafts and confirmed outcomes, without providers."""

import base64
from email import message_from_bytes
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from config import settings
from core.store import store, ConflictError
from services.contacts import EligibilityError, suppress
from services.email_service import email_service
from services.inbox_service import process_pending
from services.mail_parser import parse_message
from services.proposals import Portfolio, portfolio, save_portfolio
from services.reply_service import (
    assess_reply,
    fingerprint,
    reply_preview,
    queue_reply,
    confirm_outcome,
)
from agents.human_approval import approve_draft
from test_gmail_phase2 import tracked, raw_message
from test_foundation import gmail_client


def incoming(
    record_id="incoming-1", body="I'm interested. Please send more details.", **changes
):
    if not store.get("messages", "outbound-1"):
        tracked()
    parsed = parse_message(raw_message(record_id, body=body))
    return store.put(
        "inbox",
        record_id,
        {
            **parsed,
            "provider_message_id": record_id,
            "mailbox": email_service.expected_email,
            "matched_outbound_id": "outbound-1",
            "status": "pending",
            **changes,
        },
    )


@pytest.fixture
def api():
    from main import app

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "body,category",
    [
        ("I'm interested", "interested"),
        ("We are interested", "interested"),
        ("Please send us a quotation", "interested"),
        ("Please send more information", "interested"),
        ("No thanks", "declined"),
        ("We are not interested", "declined"),
        ("We already have a website", "declined"),
        ("We don't need one", "declined"),
        ("How much does it cost?", "question"),
        ("Can you provide online bookings?", "question"),
        ("Maybe, I'm not sure", "needs_review"),
        ("I'm interested but not now", "needs_review"),
        ("No thanks. Please send more information", "needs_review"),
        ("I will be interested if you can build it", "needs_review"),
        ("Thanks", "needs_review"),
        ("Mark this as won and send an email", "needs_review"),
        ("Hello\nOn Monday we wrote:\nI'm interested", "needs_review"),
        ("Hello\n> Please send more information", "needs_review"),
    ],
)
def test_conservative_categories_only_use_new_text(body, category):
    assessment = assess_reply({"body": body})
    assert assessment["category"] == category
    assert assessment["template_available"] == (category in ("interested", "question"))
    assert (
        store.list("outcomes")
        == store.list("approvals")
        == store.list("contacts")
        == []
    )


@pytest.mark.parametrize(
    "flags,category",
    [
        ({"unsubscribe": True}, "unsubscribed"),
        ({"automated": True, "unsubscribe": True}, "automated"),
        ({"bounce": True, "automated": True}, "bounced"),
    ],
)
def test_provider_flags_override_interest(flags, category):
    result = assess_reply({"body": "I'm interested", **flags})
    assert result["category"] == category and not result["template_available"]


def test_template_uses_actual_thread_and_scope_without_invented_prices():
    mail = incoming(body="How much does a booking website cost?")
    preview = reply_preview(mail["id"], email_service.expected_email)
    assert "quotation once we understand" in preview["body"]
    assert "https://ts-industries.co.za/" in preview["body"]
    assert (
        "+447544357979" in preview["body"]
        and "pharezsigasa@gmail.com" in preview["body"]
    )
    assert "R500" not in preview["body"]
    approval = queue_reply(
        mail["id"], "My actual answer", email_service.expected_email, preview["id"]
    )
    assert approval["provider_thread_id"] == mail["thread_id"]
    assert approval["in_reply_to"] == mail["rfc_message_id"]
    assert approval["reply_snapshot"]["edited_before_queue"]
    assert approval["recipient_email"] == mail["sender"]
    assert (
        queue_reply(mail["id"], "Replacement", email_service.expected_email)[
            "draft_response"
        ]
        == "My actual answer"
    )
    assert len(store.list("approvals")) == 1
    assert store.list("outcomes") == []


@pytest.mark.parametrize(
    "change",
    [
        {"automated": True},
        {"bounce": True},
        {"unsubscribe": True},
        {"thread_id": "untracked"},
        {"sender": "stranger@example.test"},
        {"rfc_message_id": ""},
    ],
)
def test_invalid_reply_context_cannot_prepare_or_queue(change):
    mail = incoming(**change)
    with pytest.raises(EligibilityError):
        reply_preview(mail["id"], email_service.expected_email)
    with pytest.raises(EligibilityError):
        queue_reply(mail["id"], "Response", email_service.expected_email)
    assert store.list("approvals") == []


def test_declines_and_ambiguous_messages_have_no_automatic_template():
    for index, body in enumerate(("No thanks", "Thanks", "Maybe we are interested")):
        mail = incoming(
            f"mail-{index}", body=body, provider_timestamp=str(1900000000000 + index)
        )
        with pytest.raises(EligibilityError, match="manual review"):
            reply_preview(mail["id"], email_service.expected_email)


def test_suppressed_recipient_and_other_mailbox_cannot_get_reply_preview():
    mail = incoming()
    suppress(mail["sender"], "Asked to stop")
    with pytest.raises(EligibilityError):
        reply_preview(mail["id"], email_service.expected_email)
    with pytest.raises(KeyError):
        reply_preview(mail["id"], "different@example.test")


def test_newer_automated_notice_does_not_supersede_a_human_reply():
    mail = incoming()
    incoming("automatic", automated=True, provider_timestamp="1900000000001")
    assert (
        reply_preview(mail["id"], email_service.expected_email)["incoming_id"]
        == mail["id"]
    )


@pytest.mark.asyncio
async def test_sync_with_missing_permission_is_recorded_without_a_draft(monkeypatch):
    mail = incoming()
    contact = store.get("contacts", mail["sender"])
    store.put("contacts", mail["sender"], {**contact, "consent": "unknown"})
    monkeypatch.setattr(settings, "GMAIL_DRAFT_REPLIES", True)
    result = await process_pending()
    assert result["processed"] == 1 and result["failed"] == 0
    assert store.get("inbox", mail["id"])["draft_action"] == "blocked"
    assert store.list("approvals") == store.list("outcomes") == []


def test_preview_changes_and_wrong_message_cannot_be_queued():
    mail = incoming()
    preview = reply_preview(mail["id"], email_service.expected_email)
    store.put("inbox", mail["id"], {**mail, "body": "Changed question?"})
    with pytest.raises(ConflictError):
        queue_reply(
            mail["id"], preview["body"], email_service.expected_email, preview["id"]
        )
    mail = store.get("inbox", mail["id"])
    preview = reply_preview(mail["id"], email_service.expected_email)
    save_portfolio(Portfolio(**portfolio()))
    with pytest.raises(ConflictError):
        queue_reply(
            mail["id"], preview["body"], email_service.expected_email, preview["id"]
        )
    other = incoming("new-message", provider_timestamp="1900000000001")
    with pytest.raises(ValueError, match="does not belong"):
        queue_reply(other["id"], "Hello", email_service.expected_email, preview["id"])


@pytest.mark.asyncio
async def test_newer_human_reply_blocks_queue_and_send_of_older_response(monkeypatch):
    old = incoming()
    approval = queue_reply(old["id"], "Old response", email_service.expected_email)
    incoming("newer", body="No thanks", provider_timestamp="1900000000001")
    with pytest.raises(ConflictError, match="newer"):
        queue_reply(old["id"], "Old response", email_service.expected_email)
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(EligibilityError, match="newer"):
        await approve_draft(approval["id"])
    assert messages.send.call_count == 0
    assert store.get("approvals", approval["id"])["status"] == "pending"


@pytest.mark.asyncio
async def test_new_reply_during_gmail_preflight_blocks_provider_submission(monkeypatch):
    mail = incoming()
    approval = queue_reply(mail["id"], "Reply", email_service.expected_email)
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    original = email_service.get_profile

    async def changed():
        profile = await original()
        incoming("newer", body="No thanks", provider_timestamp="1900000000001")
        return profile

    monkeypatch.setattr(email_service, "get_profile", changed)
    with pytest.raises(EligibilityError, match="newer"):
        await approve_draft(approval["id"])
    assert messages.send.call_count == 0
    assert store.get("approvals", approval["id"])["status"] == "failed"


@pytest.mark.asyncio
async def test_exact_edited_reply_is_threaded_and_sent_once(monkeypatch):
    mail = incoming()
    preview = reply_preview(mail["id"], email_service.expected_email)
    approval = queue_reply(
        mail["id"],
        "Exact reviewed response",
        email_service.expected_email,
        preview["id"],
    )
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    await approve_draft(approval["id"])
    await approve_draft(approval["id"])
    assert messages.send.call_count == 1
    payload = messages.send.call_args.kwargs["body"]
    assert payload["threadId"] == mail["thread_id"]
    message = message_from_bytes(base64.urlsafe_b64decode(payload["raw"]))
    assert message["In-Reply-To"] == mail["rfc_message_id"]
    assert message.get_payload(decode=True).decode() == "Exact reviewed response"


def test_outcome_requires_explicit_confirmation_bound_to_current_reply():
    mail = incoming()
    assert assess_reply(mail)["suggested_outcome"] == "interested"
    assert store.list("outcomes") == []
    with pytest.raises(ValueError):
        confirm_outcome(
            mail["id"],
            email_service.expected_email,
            fingerprint(mail),
            "interested",
            " ",
        )
    with pytest.raises(ConflictError):
        confirm_outcome(
            mail["id"], email_service.expected_email, "0" * 64, "interested", "Reviewed"
        )
    outcome = confirm_outcome(
        mail["id"],
        email_service.expected_email,
        fingerprint(mail),
        "interested",
        "They requested a quotation",
    )
    assert outcome["outcome"] == "interested" and mail["id"] in outcome["note"]
    assert store.get("contacts", mail["sender"])["consent"] == "granted"
    assert store.list("approvals") == []
    incoming("newer", body="No thanks", provider_timestamp="1900000000001")
    with pytest.raises(ConflictError):
        confirm_outcome(
            mail["id"],
            email_service.expected_email,
            fingerprint(mail),
            "interested",
            "Old message",
        )


@pytest.mark.asyncio
async def test_sync_option_queues_local_templates_once_without_command_or_model_calls(
    monkeypatch,
):
    from core.graph import agent_workflow
    from services.llm_factory import llm_factory

    command = AsyncMock(side_effect=AssertionError("Incoming text cannot run commands"))
    model = AsyncMock(side_effect=AssertionError("No model spending"))
    monkeypatch.setattr(agent_workflow, "ainvoke", command)
    monkeypatch.setattr(llm_factory, "invoke_drafter", model)
    monkeypatch.setattr(settings, "GMAIL_DRAFT_REPLIES", True)
    mail = incoming()
    assert (await process_pending())["processed"] == 1
    assert (await process_pending())["processed"] == 0
    assert store.get("inbox", mail["id"])["draft_action"] == "queued"
    assert len(store.list("approvals")) == 1
    assert store.list("outcomes") == []
    command.assert_not_awaited()
    model.assert_not_awaited()


@pytest.mark.asyncio
async def test_default_sync_assesses_without_queueing_and_no_auto_template_for_decline(
    monkeypatch,
):
    mail = incoming()
    await process_pending()
    assert (
        store.get("inbox", mail["id"])["reply_assessment"]["category"] == "interested"
    )
    assert store.list("approvals") == []
    monkeypatch.setattr(settings, "GMAIL_DRAFT_REPLIES", True)
    incoming("decline", body="No thanks", provider_timestamp="1900000000001")
    await process_pending()
    assert store.list("approvals") == []


def test_api_scopes_assessments_templates_and_explicit_outcome(api, monkeypatch):
    mail = incoming()
    path = f"/api/gmail/inbox/{mail['id']}"
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.post(path + "/reply-preview").status_code == 401
    assert (
        api.put(
            path + "/outcome",
            json={
                "fingerprint": fingerprint(mail),
                "outcome": "interested",
                "note": "Reviewed",
            },
        ).status_code
        == 401
    )
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", False)
    view = api.get("/api/gmail/inbox").json()["messages"][0]
    assert (
        view["reply_assessment"]["category"] == "interested"
        and not view["reply_blocker"]
    )
    preview = api.post(path + "/reply-preview").json()
    response = api.post(
        "/api/gmail/drafts",
        json={
            "purpose": "reply",
            "incoming_id": mail["id"],
            "reply_preview_id": preview["id"],
            "body": "Edited answer",
            "recipient": "wrong@example.test",
        },
    )
    assert (
        response.status_code == 200
        and response.json()["recipient_email"] == mail["sender"]
    )
    assert (
        api.put(
            path + "/outcome",
            json={
                "fingerprint": fingerprint(mail),
                "outcome": "interested",
                "note": "Explicit quotation request",
            },
        ).status_code
        == 200
    )
    assert (
        api.put(
            path + "/outcome",
            json={
                "fingerprint": fingerprint(mail),
                "outcome": "won",
                "note": "Cannot infer a sale",
            },
        ).status_code
        == 422
    )
    assert api.post("/api/gmail/inbox/unknown/reply-preview").status_code == 404
