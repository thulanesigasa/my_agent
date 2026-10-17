"""Regression coverage for persistence, truthful status and dispatch boundaries."""

import base64
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from config import Settings, settings
from core.store import StateStore, ConflictError, store
from agents.human_approval import queue_approval, approve_draft, reject_or_edit_draft
from services.email_service import email_service, EmailUnavailable, DeliveryUnknown


def queue(record_id="review-1"):
    from services.contacts import save_contact

    save_contact(
        "owner@example.test",
        verified=True,
        consent="granted",
        evidence="Explicit fixture consent",
    )
    return queue_approval(
        record_id,
        {
            "recipient_email": "owner@example.test",
            "subject": "Reviewed subject",
            "draft_response": "Reviewed body",
            "intent": "sales",
            "purpose": "outreach",
        },
    )


def gmail_client(message=None, error=None):
    request = Mock()
    request.execute.side_effect = error
    request.execute.return_value = message or {
        "id": "provider-1",
        "threadId": "gmail-thread-1",
    }
    messages = Mock()
    messages.send.return_value = request
    return (
        SimpleNamespace(
            users=lambda: SimpleNamespace(
                messages=lambda: messages,
                getProfile=lambda **kwargs: SimpleNamespace(
                    execute=lambda **kwargs: {
                        "emailAddress": "sender@example.test",
                        "historyId": "100",
                    }
                ),
            )
        ),
        messages,
    )


def test_records_survive_process_restart(isolated_state):
    for kind in ("leads", "tasks", "approvals", "messages", "clients"):
        store.put(kind, "saved", {"status": "pending", "value": kind})
    code = "from core.store import store; assert all(store.get(k, 'saved')['value'] == k for k in ('leads','tasks','approvals','messages','clients'))"
    subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "STATE_DB_PATH": store.path},
        check=True,
    )


def test_atomic_dispatch_claim_across_connections(isolated_state):
    queue()

    def claim(_):
        try:
            StateStore(store.path).transition(
                "approvals", "review-1", ["pending"], "sending"
            )
            return True
        except ConflictError:
            return False

    with ThreadPoolExecutor(max_workers=6) as workers:
        assert sum(workers.map(claim, range(6))) == 1


@pytest.mark.asyncio
async def test_approval_sends_exact_saved_draft_once(monkeypatch):
    queue()
    client, messages = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    await approve_draft("review-1")
    result = await approve_draft("review-1")
    assert result["already_sent"]
    assert messages.send.call_count == 1
    payload = messages.send.call_args.kwargs["body"]
    assert "threadId" not in payload  # Internal approval ID is not a Gmail thread ID.
    from email import message_from_bytes

    msg = message_from_bytes(base64.urlsafe_b64decode(payload["raw"]))
    assert msg["To"] == "owner@example.test"
    assert msg["Subject"] == "Reviewed subject"
    assert msg.get_payload(decode=True).decode() == "Reviewed body"
    assert store.metrics()["totalEmailsSent"] == 1
    assert store.get("approvals", "review-1")["status"] == "sent"


@pytest.mark.asyncio
async def test_missing_gmail_never_counts_as_sent():
    queue()
    with pytest.raises(EmailUnavailable):
        await approve_draft("review-1")
    assert store.get("approvals", "review-1")["status"] == "failed"
    assert store.email_logs() == []
    with pytest.raises(EmailUnavailable):
        await email_service.fetch_unread_emails()


@pytest.mark.asyncio
async def test_unknown_delivery_is_held_and_cannot_resend(monkeypatch):
    queue()
    client, messages = gmail_client(error=TimeoutError("Connection lost after request"))
    monkeypatch.setattr(email_service, "client", client)
    with pytest.raises(DeliveryUnknown):
        await approve_draft("review-1")
    assert store.get("approvals", "review-1")["status"] == "delivery_unknown"
    with pytest.raises(ConflictError):
        await approve_draft("review-1")
    assert messages.send.call_count == 1
    assert store.email_logs() == []


@pytest.mark.asyncio
async def test_edit_saves_without_sending_and_reject_is_final(monkeypatch):
    queue()
    send = Mock(side_effect=AssertionError("Must not send"))
    monkeypatch.setattr(email_service, "send_email", send)
    await reject_or_edit_draft("review-1", "Updated draft")
    assert store.get("approvals", "review-1")["draft_response"] == "Updated draft"
    await reject_or_edit_draft("review-1")
    with pytest.raises(ConflictError):
        await approve_draft("review-1")
    send.assert_not_called()


def test_rediscovery_cannot_replace_reviewed_or_sent_content():
    queue()
    store.transition(
        "approvals", "review-1", ["pending"], "sent", provider_message_id="provider-1"
    )
    queue_approval(
        "review-1",
        {
            "recipient_email": "different@example.test",
            "subject": "New",
            "draft_response": "New",
        },
    )
    assert store.get("approvals", "review-1")["draft_response"] == "Reviewed body"


@pytest.mark.asyncio
async def test_notification_is_not_outreach(monkeypatch):
    client, _ = gmail_client()
    monkeypatch.setattr(email_service, "client", client)
    await email_service.send_email(
        "admin@example.test", "Notification", "A draft needs review"
    )
    assert store.email_logs() == []


@pytest.mark.asyncio
async def test_discovery_has_no_fake_leads_or_contacts():
    from tools.lead_finder import search_businesses_without_websites, find_contact_email

    with pytest.raises(RuntimeError, match="unavailable"):
        await search_businesses_without_websites()
    assert (await find_contact_email("Unknown company"))["email"] is None


@pytest.mark.asyncio
async def test_llm_unavailable_raises_instead_of_claiming_success():
    from services.llm_factory import llm_factory

    with pytest.raises(RuntimeError, match="unavailable"):
        await llm_factory.invoke_drafter("Write a pitch")


@pytest.mark.asyncio
async def test_weekly_reports_cannot_send_example_figures():
    from services.report_service import send_weekly_report

    with pytest.raises(RuntimeError, match="disabled"):
        await send_weekly_report()


@pytest.mark.asyncio
async def test_graph_checkpoints_and_approval_survive_new_graph(fake_llm):
    from core.graph import PersistentWorkflow
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    state = {
        "messages": [{"role": "user", "content": "Can you build our website?"}],
        "email_input": {
            "id": "in-1",
            "thread_id": "provider-thread",
            "sender": "owner@example.test",
            "subject": "Website",
            "body": "Please share more information",
        },
    }
    result = await PersistentWorkflow().ainvoke(
        state, config={"configurable": {"thread_id": "conversation-1"}}
    )
    assert result["needs_human_approval"]
    assert (
        store.get("approvals", "reply_in-1")["provider_thread_id"] == "provider-thread"
    )
    async with AsyncSqliteSaver.from_conn_string(
        store.path + ".checkpoints.sqlite3"
    ) as saver:
        saved = await saver.aget_tuple(
            {"configurable": {"thread_id": "conversation-1"}}
        )
        assert (
            saved.checkpoint["channel_values"]["draft_response"]
            == result["draft_response"]
        )
    assert store.list("tasks")[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_inbox_repeated_notifications_only_run_once(monkeypatch):
    from services.inbox_service import process_inbox_batch
    from core.graph import agent_workflow

    mail = {"id": "in-1", "thread_id": "gmail-1", "body": "Hi"}

    store.put(
        "messages",
        "sent-1",
        {
            "status": "sent",
            "thread_id": "gmail-1",
            "purpose": "test",
            "to": "owner@example.test",
            "from": "sender@example.test",
        },
    )
    mail.update(sender="owner@example.test", rfc_message_id="<reply@test>")
    monkeypatch.setattr(settings, "GMAIL_DRAFT_REPLIES", True)

    async def sync(*args):
        return {
            "messages": [mail],
            "mailbox": "sender@example.test",
            "history_id": "101",
            "full_sync": False,
        }

    calls = []

    async def run(*args, **kwargs):
        calls.append(args)
        return {}

    monkeypatch.setattr(email_service, "sync_mailbox", sync)
    monkeypatch.setattr(agent_workflow, "ainvoke", run)
    assert (await process_inbox_batch())["processed"] == 1
    assert (await process_inbox_batch())["processed"] == 0
    assert len(calls) == 1


@pytest.fixture
def api():
    from main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client


def test_approval_api_missing_id_edit_failure_and_auth(api, monkeypatch):
    assert (
        api.post(
            "/api/approvals/missing/action", json={"action": "approve"}
        ).status_code
        == 404
    )
    queue()
    assert (
        api.post(
            "/api/approvals/review-1/action",
            json={"action": "edit", "new_content": " "},
        ).status_code
        == 400
    )
    assert (
        api.post(
            "/api/approvals/review-1/action", json={"action": "approve"}
        ).status_code
        == 503
    )
    assert api.get("/api/outreach/logs").json()["logs"] == []
    assert api.get("/api/outreach/metrics").json()["metrics"]["totalEmailsSent"] == 0
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    assert api.get("/api/outreach/logs").status_code == 401
    assert api.get("/api/outreach/metrics").status_code == 401


def test_webhook_rejects_unconfigured_wrong_and_malformed_requests(api, monkeypatch):
    assert api.post("/webhooks/gmail", json={}).status_code == 503
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", "exact-secret")
    for token in ("", "wrong", "prefix-exact-secret-suffix"):
        assert (
            api.post(
                "/webhooks/gmail", headers={"X-Goog-PubSub-Token": token}, json={}
            ).status_code
            == 403
        )
    assert api.post("/webhooks/gmail?token=exact-secret", json={}).status_code == 403
    assert (
        api.post(
            "/webhooks/gmail", headers={"X-Goog-PubSub-Token": "exact-secret"}, json={}
        ).status_code
        == 400
    )


def test_valid_webhook_without_gmail_does_not_acknowledge_processing(api, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", "exact-secret")
    data = base64.b64encode(
        json.dumps({"historyId": "123", "emailAddress": "sender@example.test"}).encode()
    ).decode()
    response = api.post(
        "/webhooks/gmail",
        headers={"X-Goog-PubSub-Token": "exact-secret"},
        json={"message": {"data": data}},
    )
    assert response.status_code == 503


def test_production_rejects_unprotected_api():
    with pytest.raises(ValueError, match="Production requires"):
        Settings(ENV="production", API_KEY_REQUIRED=False, _env_file=None)


def test_workflow_claim_blocks_other_processes_until_released():
    store.claim_workflow("thread-1")
    with pytest.raises(ConflictError):
        StateStore(store.path).claim_workflow("thread-1")
    store.transition("threads", "thread-1", ["running"], "idle")
    StateStore(store.path).claim_workflow("thread-1")


@pytest.mark.asyncio
async def test_local_crm_and_memory_persist():
    from services.crm_service import (
        upsert_client,
        update_project_status,
        get_all_clients,
    )
    from core.memory import MemoryManager, memory_manager

    await upsert_client("Test Business", "owner@example.test")
    await update_project_status("owner@example.test", "Lead")
    assert (await get_all_clients())[0]["name"] == "Test Business"
    await memory_manager.save_memory("Prefers a blue website")
    assert (await MemoryManager().search_memory("blue"))[0]["value"][
        "content"
    ] == "Prefers a blue website"
    assert StateStore(store.path).list("projects")[0]["status"] == "Lead"


@pytest.mark.asyncio
async def test_configured_crm_failure_cannot_fall_back(monkeypatch):
    from services import crm_service

    client = Mock()
    client.table.side_effect = RuntimeError("Configured remote storage unavailable")
    monkeypatch.setattr(crm_service, "_get_supabase_client", lambda: client)
    with pytest.raises(RuntimeError, match="unavailable"):
        await crm_service.upsert_client("Test Business", "owner@example.test")
    assert store.list("clients") == []


@pytest.mark.asyncio
async def test_workflow_failure_is_recorded_and_thread_released(monkeypatch):
    from core.graph import PersistentWorkflow
    from services.llm_factory import llm_factory

    async def fail(*args, **kwargs):
        raise RuntimeError("Provider failed")

    monkeypatch.setattr(llm_factory, "invoke_triage", fail)
    with pytest.raises(RuntimeError, match="Provider failed"):
        await PersistentWorkflow().ainvoke(
            {"messages": [{"role": "user", "content": "Hi"}]},
            config={"configurable": {"thread_id": "failed-thread"}},
        )
    assert store.list("tasks")[0]["status"] == "failed"
    assert store.get("threads", "failed-thread")["status"] == "idle"


@pytest.mark.asyncio
async def test_search_candidates_are_persisted_without_claiming_verification(
    monkeypatch,
):
    from tools import lead_finder

    class SearchClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    "results": [
                        {
                            "title": "Test Bakery",
                            "url": "https://directory.example.test/bakery",
                        }
                    ]
                },
            )

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(
        lead_finder.httpx, "AsyncClient", lambda **kwargs: SearchClient()
    )
    leads = await lead_finder.search_businesses_without_websites("Test Town")
    assert len(leads) == 1
    assert leads[0]["missing_website"] is None
    assert leads[0]["requires_review"]
    assert leads[0]["source_url"] == "https://directory.example.test/bakery"
    assert len(StateStore(store.path).list("leads")) == 1
