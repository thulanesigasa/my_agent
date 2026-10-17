"""Offline Gmail integration tests; all provider responses are explicit fixtures."""

import base64
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from auth.gmail_credentials import SCOPES, load_credentials
from agents.human_approval import approve_draft, queue_approval
from config import settings
from core.store import store, ConflictError
from services.contacts import save_contact, suppress, EligibilityError
from services.email_service import email_service, EmailUnavailable, DeliveryUnknown
from services.inbox_service import process_inbox_batch
from services.mail_parser import parse_message


def response(data=None, error=None):
    def execute(**kwargs):
        if error:
            raise error
        return data

    return SimpleNamespace(execute=execute)


def http_error(status):
    return HttpError(
        SimpleNamespace(status=status, reason="Provider error"), b'{"error":"fixture"}'
    )


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


def raw_message(
    message_id="incoming-1",
    thread="thread-1",
    sender="owner@example.test",
    body="Thanks, please send more information",
    **extra,
):
    return {
        "id": message_id,
        "threadId": thread,
        "internalDate": "1900000000000",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "To", "value": "sender@example.test"},
                {"name": "Subject", "value": "Re: Website"},
                {"name": "Message-ID", "value": f"<{message_id}@example.test>"},
            ],
            "body": {"data": encoded(body)},
        },
        **extra,
    }


class FakeGmail:
    def __init__(self):
        self.profile = {"emailAddress": "sender@example.test", "historyId": "150"}
        self.profile_error = None
        self.send_error = None
        self.send_calls = []
        self.message_data = {}
        self.thread_data = {}
        self.history_pages = {None: {"history": [], "historyId": "151"}}
        self.history_error = None
        self.history_calls = []
        self.search_results = []
        self.messages_api = SimpleNamespace(
            get=self.get_message, send=self.send, list=self.search
        )
        self.threads_api = SimpleNamespace(get=self.get_thread)
        self.history_api = SimpleNamespace(list=self.get_history)

    def users(self):
        return self

    def messages(self):
        return self.messages_api

    def threads(self):
        return self.threads_api

    def history(self):
        return self.history_api

    def getProfile(self, **kwargs):
        return response(self.profile, self.profile_error)

    def get_message(self, id, **kwargs):
        return response(
            self.message_data.get(id),
            http_error(404) if id not in self.message_data else None,
        )

    def get_thread(self, id, **kwargs):
        return response({"messages": self.thread_data.get(id, [])})

    def get_history(self, **kwargs):
        self.history_calls.append(kwargs)
        return response(self.history_pages[kwargs.get("pageToken")], self.history_error)

    def search(self, **kwargs):
        return response({"messages": self.search_results})

    def send(self, **kwargs):
        self.send_calls.append(kwargs)
        return response(
            {"id": "sent-provider-1", "threadId": "thread-1"}, self.send_error
        )


@pytest.fixture
def gmail(monkeypatch):
    fake = FakeGmail()
    monkeypatch.setattr(email_service, "client", fake)
    return fake


def tracked(purpose="outreach", to="owner@example.test"):
    save_contact(
        to,
        verified=True,
        consent="granted",
        evidence="Explicit fixture consent",
        test_recipient=True,
    )
    return store.put(
        "messages",
        "outbound-1",
        {
            "status": "sent",
            "from": "sender@example.test",
            "to": to,
            "thread_id": "thread-1",
            "purpose": purpose,
            "subject": "Website",
            "body": "Website proposal",
        },
    )


def approval(purpose="outreach"):
    return queue_approval(
        "review-1",
        {
            "recipient_email": "owner@example.test",
            "subject": "Website",
            "draft_response": "Reviewed body",
            "purpose": purpose,
        },
    )


@pytest.mark.asyncio
async def test_profile_checks_selected_account_and_no_send(gmail):
    profile = await email_service.get_profile()
    assert profile["emailAddress"] == "sender@example.test"
    assert store.get("gmail_connection", "current")["status"] == "verified"
    gmail.profile["emailAddress"] = "wrong@example.test"
    with pytest.raises(EmailUnavailable, match="does not match"):
        await email_service.get_profile()
    assert gmail.send_calls == []


@pytest.mark.asyncio
async def test_revoked_token_records_reauthorization(gmail):
    gmail.profile_error = RefreshError("invalid_grant")
    with pytest.raises(EmailUnavailable, match="authorisation expired"):
        await email_service.get_profile()
    assert (
        store.get("gmail_connection", "current")["status"] == "reauthorization_required"
    )
    assert gmail.send_calls == []


@pytest.mark.asyncio
async def test_unknown_or_suppressed_contact_cannot_send(gmail):
    approval()
    with pytest.raises(EligibilityError):
        await approve_draft("review-1")
    save_contact(
        "owner@example.test",
        verified=True,
        consent="granted",
        evidence="Permission recorded",
    )
    suppress("owner@example.test", "Opted out")
    with pytest.raises(EligibilityError, match="do-not-contact"):
        await approve_draft("review-1")
    assert gmail.send_calls == []


@pytest.mark.asyncio
async def test_eligibility_is_checked_again_immediately_before_submit(
    gmail, monkeypatch
):
    tracked()
    approval()
    original = email_service.get_profile

    async def changed():
        profile = await original()
        suppress("owner@example.test", "Opted out during preflight")
        return profile

    monkeypatch.setattr(email_service, "get_profile", changed)
    with pytest.raises(EligibilityError):
        await approve_draft("review-1")
    assert gmail.send_calls == []
    assert store.get("approvals", "review-1")["status"] == "failed"


@pytest.mark.asyncio
async def test_test_address_does_not_grant_marketing_permission(gmail):
    save_contact(
        "owner@example.test", test_recipient=True, evidence="I control the test inbox"
    )
    approval("test")
    assert (await approve_draft("review-1"))["status"] == "sent"
    queue_approval(
        "marketing",
        {
            "recipient_email": "owner@example.test",
            "subject": "Website",
            "draft_response": "Offer",
            "purpose": "outreach",
        },
    )
    with pytest.raises(EligibilityError):
        await approve_draft("marketing")
    assert store.email_logs() == []


@pytest.mark.asyncio
async def test_reply_headers_and_provider_thread_match(gmail):
    tracked()
    queue_approval(
        "reply-1",
        {
            "recipient_email": "owner@example.test",
            "subject": "Re: Website",
            "draft_response": "Here is more information",
            "purpose": "reply",
            "provider_thread_id": "thread-1",
            "in_reply_to": "<incoming@example.test>",
            "references": "<original@example.test>",
        },
    )
    await approve_draft("reply-1")
    from email import message_from_bytes

    payload = gmail.send_calls[0]["body"]
    message = message_from_bytes(base64.urlsafe_b64decode(payload["raw"]))
    assert payload["threadId"] == "thread-1"
    assert message["In-Reply-To"] == "<incoming@example.test>"
    assert "<original@example.test>" in message["References"]
    assert message["Message-ID"]


@pytest.mark.asyncio
async def test_explicit_gmail_rejection_is_failed_not_unknown(gmail):
    tracked()
    approval()
    gmail.send_error = http_error(429)
    with pytest.raises(EmailUnavailable, match="rejected"):
        await approve_draft("review-1")
    assert store.get("approvals", "review-1")["status"] == "failed"
    assert len(gmail.send_calls) == 1


@pytest.mark.asyncio
async def test_reconcile_unknown_send_does_not_send_again(gmail):
    tracked()
    approval()
    gmail.send_error = TimeoutError("Response was lost")
    with pytest.raises(DeliveryUnknown):
        await approve_draft("review-1")
    assert (await email_service.reconcile("review-1"))["status"] == "held"
    item = store.get("approvals", "review-1")
    dispatch = store.get("messages", item["dispatch_id"])
    message = raw_message("found-sent", sender="sender@example.test", labelIds=["SENT"])
    for header in message["payload"]["headers"]:
        if header["name"] == "To":
            header["value"] = dispatch["to"]
        if header["name"] == "Subject":
            header["value"] = dispatch["subject"]
        if header["name"] == "Message-ID":
            header["value"] = dispatch["rfc_message_id"]
    gmail.message_data["found-sent"] = message
    gmail.search_results = [{"id": "found-sent"}]
    assert (await email_service.reconcile("review-1"))["reconciled"]
    assert store.get("approvals", "review-1")["status"] == "sent"
    assert len(gmail.send_calls) == 1
    assert (await approve_draft("review-1"))["already_sent"]


@pytest.mark.asyncio
async def test_reconciliation_rejects_wrong_provider_evidence(gmail):
    tracked()
    approval()
    gmail.send_error = TimeoutError()
    with pytest.raises(DeliveryUnknown):
        await approve_draft("review-1")
    gmail.search_results = [{"id": "wrong"}]
    gmail.message_data["wrong"] = raw_message("wrong", labelIds=["SENT"])
    assert (await email_service.reconcile("review-1"))["status"] == "held"
    assert store.get("approvals", "review-1")["status"] == "delivery_unknown"


@pytest.mark.asyncio
async def test_full_sync_records_read_and_archived_replies_only_once(gmail):
    tracked()
    gmail.thread_data["thread-1"] = [raw_message(labelIds=[])]
    first = await process_inbox_batch()
    second = await process_inbox_batch()
    assert first["recorded"] == 1
    assert second["recorded"] == 0
    assert len(store.list("inbox")) == 1
    assert store.email_logs()[0]["status"] == "Responded"
    assert store.get("gmail_cursor", "sender@example.test")["history_id"] == "151"


@pytest.mark.asyncio
async def test_history_paginates_and_ignores_untracked_mail(gmail):
    tracked()
    store.put("gmail_cursor", "sender@example.test", {"history_id": "100"})
    gmail.history_pages = {
        None: {
            "history": [
                {
                    "messagesAdded": [
                        {"message": {"id": "incoming-1", "threadId": "thread-1"}},
                        {"message": {"id": "private", "threadId": "other-thread"}},
                    ]
                }
            ],
            "nextPageToken": "next",
            "historyId": "151",
        },
        "next": {
            "history": [
                {
                    "messagesAdded": [
                        {"message": {"id": "incoming-2", "threadId": "thread-1"}}
                    ]
                }
            ],
            "historyId": "152",
        },
    }
    gmail.message_data = {
        "incoming-1": raw_message(),
        "incoming-2": raw_message("incoming-2"),
    }
    result = await process_inbox_batch()
    assert result["recorded"] == 2
    assert len(gmail.history_calls) == 2
    assert store.get("gmail_cursor", "sender@example.test")["history_id"] == "152"
    assert len(store.list("inbox")) == 2


@pytest.mark.asyncio
async def test_expired_history_rescans_tracked_threads(gmail):
    tracked()
    store.put("gmail_cursor", "sender@example.test", {"history_id": "old"})
    gmail.history_error = http_error(404)
    gmail.thread_data["thread-1"] = [raw_message()]
    result = await process_inbox_batch()
    assert result["full_sync"]
    assert store.get("gmail_cursor", "sender@example.test")["history_id"] == "150"


@pytest.mark.asyncio
async def test_sync_failure_does_not_advance_cursor(gmail):
    tracked()
    store.put("gmail_cursor", "sender@example.test", {"history_id": "100"})
    gmail.history_error = RuntimeError("Network interrupted")
    with pytest.raises(RuntimeError):
        await process_inbox_batch()
    assert store.get("gmail_cursor", "sender@example.test")["history_id"] == "100"
    assert store.get("leases", "gmail-sync") is None


@pytest.mark.asyncio
async def test_sync_page_limit_cannot_drop_unread_history(gmail, monkeypatch):
    tracked()
    store.put("gmail_cursor", "sender@example.test", {"history_id": "100"})
    monkeypatch.setattr(settings, "GMAIL_SYNC_MAX_PAGES", 1)
    gmail.history_pages = {
        None: {"history": [], "nextPageToken": "next", "historyId": "151"}
    }
    with pytest.raises(EmailUnavailable, match="page limit"):
        await process_inbox_batch()
    assert store.get("gmail_cursor", "sender@example.test")["history_id"] == "100"


@pytest.mark.asyncio
async def test_opt_out_is_saved_even_when_optional_ai_fails(gmail, monkeypatch):
    tracked()
    gmail.thread_data["thread-1"] = [raw_message(body="Please stop emailing me")]
    monkeypatch.setattr(settings, "GMAIL_DRAFT_REPLIES", True)
    from core.graph import agent_workflow

    async def must_not_draft(*args, **kwargs):
        raise AssertionError("An opt-out must not be sent to the drafter")

    monkeypatch.setattr(agent_workflow, "ainvoke", must_not_draft)
    assert (await process_inbox_batch())["processed"] == 1
    assert store.get("contacts", "owner@example.test")["consent"] == "unsubscribed"


@pytest.mark.asyncio
async def test_automated_replies_and_unexpected_senders_are_not_human_replies(gmail):
    tracked()
    auto = raw_message()
    auto["payload"]["headers"].append(
        {"name": "Auto-Submitted", "value": "auto-replied"}
    )
    gmail.thread_data["thread-1"] = [
        auto,
        raw_message("stranger", sender="stranger@example.test"),
    ]
    assert (await process_inbox_batch())["recorded"] == 1
    assert store.email_logs()[0]["status"] == "Sent"


def test_mime_nested_plain_body_is_not_the_snippet_and_quoted_opt_out_is_ignored():
    message = raw_message(body="")
    message["snippet"] = "Wrong incomplete text"
    message["payload"]["mimeType"] = "multipart/mixed"
    message["payload"]["parts"] = [
        {
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {"data": encoded("<p>HTML alternative</p>")},
                },
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": encoded(
                            "Full reply\n\nOn Friday someone wrote:\n> unsubscribe"
                        )
                    },
                },
            ],
        },
        {
            "mimeType": "text/plain",
            "filename": "attachment.txt",
            "body": {"data": encoded("unsubscribe")},
        },
    ]
    parsed = parse_message(message)
    assert parsed["body"] == "Full reply"
    assert not parsed["unsubscribe"]


def test_html_fallback_strips_scripts_and_quoted_text():
    message = raw_message()
    message["payload"]["mimeType"] = "text/html"
    message["payload"]["body"] = {
        "data": encoded(
            "<p>Hello &amp; thanks</p><script>bad()</script><blockquote>unsubscribe</blockquote>"
        )
    }
    parsed = parse_message(message)
    assert parsed["body"] == "Hello & thanks"
    assert not parsed["unsubscribe"]


def test_mailbox_lease_prevents_concurrent_sync_and_recovers_expired_owner():
    store.acquire_lease("gmail-sync", "worker-1")
    with pytest.raises(ConflictError):
        store.acquire_lease("gmail-sync", "worker-2")
    store.put("leases", "gmail-sync", {"owner": "worker-1", "expires": 0})
    store.acquire_lease("gmail-sync", "worker-2")
    with pytest.raises(ConflictError):
        store.ingest_mailbox("worker-1", "sender@example.test", "100", [])


@pytest.mark.asyncio
async def test_drafting_failure_retains_reply_and_does_not_stall_history(
    gmail, monkeypatch
):
    tracked()
    gmail.thread_data["thread-1"] = [raw_message()]
    monkeypatch.setattr(settings, "GMAIL_DRAFT_REPLIES", True)
    from core.graph import agent_workflow

    async def fail(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(agent_workflow, "ainvoke", fail)
    result = await process_inbox_batch()
    assert result["failed"] == 1
    assert store.list("inbox")[0]["status"] == "failed"
    assert store.get("gmail_cursor", "sender@example.test")["history_id"] == "150"
    assert store.email_logs()[0]["status"] == "Responded"


@pytest.fixture
def oauth(monkeypatch, tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    import connect_gmail

    client_file = tmp_path / "client.json"
    client_file.write_text(
        json.dumps(
            {"installed": {"client_id": "fake-id", "client_secret": "fake-secret"}}
        )
    )
    token_file = tmp_path / "private" / "token.json"
    credentials = SimpleNamespace(
        refresh_token="fake-refresh",
        scopes=SCOPES,
        granted_scopes=SCOPES,
        to_json=lambda: json.dumps(
            {
                "client_id": "fake-id",
                "client_secret": "fake-secret",
                "refresh_token": "fake-refresh",
                "scopes": SCOPES,
            }
        ),
    )
    flow = Mock()
    flow.run_local_server.return_value = credentials
    monkeypatch.setattr(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_config",
        lambda *args: flow,
    )
    profile = {"emailAddress": "sender@example.test"}
    monkeypatch.setattr(
        "googleapiclient.discovery.build",
        lambda *args, **kwargs: SimpleNamespace(
            users=lambda: SimpleNamespace(getProfile=lambda **kwargs: response(profile))
        ),
    )
    return SimpleNamespace(
        module=connect_gmail,
        client=client_file,
        token=token_file,
        profile=profile,
        credentials=credentials,
        flow=flow,
    )


def test_oauth_helper_saves_private_token_for_verified_account(oauth, monkeypatch):
    assert (
        oauth.module.authorize(oauth.client, oauth.token, "sender@example.test")
        == "sender@example.test"
    )
    data = json.loads(oauth.token.read_text())
    assert data["gmail_account"] == "sender@example.test"
    monkeypatch.setattr(settings, "GMAIL_TOKEN_PATH", str(oauth.token))
    credentials, account = load_credentials(settings)
    assert account == "sender@example.test"
    assert credentials.refresh_token == "fake-refresh"


def test_oauth_wrong_account_or_missing_scope_never_saves_token(oauth):
    oauth.profile["emailAddress"] = "wrong@example.test"
    with pytest.raises(ValueError, match="does not match"):
        oauth.module.authorize(oauth.client, oauth.token, "sender@example.test")
    assert not oauth.token.exists()
    oauth.profile["emailAddress"] = "sender@example.test"
    oauth.credentials.granted_scopes = SCOPES[:1]
    with pytest.raises(ValueError, match="both permissions"):
        oauth.module.authorize(oauth.client, oauth.token, "sender@example.test")
    assert not oauth.token.exists()


def test_web_client_requires_registered_loopback_redirect(oauth):
    oauth.client.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "fake",
                    "redirect_uris": ["https://example.test/callback"],
                }
            }
        )
    )
    with pytest.raises(ValueError, match="Register http://localhost:8765/"):
        oauth.module.authorize(oauth.client, oauth.token, "sender@example.test")
    assert not oauth.token.exists()


def test_old_token_without_read_send_scopes_is_rejected(oauth, monkeypatch):
    oauth.token.parent.mkdir()
    oauth.token.write_text(
        json.dumps(
            {
                "client_id": "fake",
                "client_secret": "fake",
                "refresh_token": "fake",
                "gmail_account": "sender@example.test",
                "scopes": SCOPES[:1],
            }
        )
    )
    monkeypatch.setattr(settings, "GMAIL_TOKEN_PATH", str(oauth.token))
    with pytest.raises(ValueError, match="Reconnect"):
        load_credentials(settings)


@pytest.fixture
def api():
    from main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client


def test_gmail_controls_require_api_key_when_enabled(api, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY_REQUIRED", True)
    for path in ("/api/gmail/status", "/api/gmail/inbox", "/api/gmail/contacts"):
        assert api.get(path).status_code == 401
    assert api.post("/api/gmail/sync").status_code == 401


def test_controlled_test_draft_is_not_sent_until_approved(api, gmail):
    payload = {"test_recipient": True, "evidence": "I control this second test mailbox"}
    assert (
        api.put("/api/gmail/contacts/owner@example.test", json=payload).status_code
        == 200
    )
    result = api.post(
        "/api/gmail/drafts",
        json={
            "recipient": "owner@example.test",
            "subject": "Connection test",
            "body": "Please reply",
            "purpose": "test",
        },
    )
    assert result.status_code == 200
    assert gmail.send_calls == []
    approval_id = result.json()["id"]
    assert (
        api.post(
            f"/api/approvals/{approval_id}/action", json={"action": "approve"}
        ).status_code
        == 200
    )
    assert len(gmail.send_calls) == 1
    assert api.post("/api/gmail/verify").json()["email"] == "sender@example.test"


def test_gmail_draft_rejects_unrecorded_consent_and_self_reply_test(api, gmail):
    assert (
        api.post(
            "/api/gmail/drafts",
            json={
                "recipient": "owner@example.test",
                "subject": "Offer",
                "body": "Website",
                "purpose": "outreach",
            },
        ).status_code
        == 403
    )
    assert (
        api.post(
            "/api/gmail/drafts",
            json={
                "recipient": "sender@example.test",
                "subject": "Test",
                "body": "Test",
                "purpose": "test",
            },
        ).status_code
        == 400
    )
    assert gmail.send_calls == []


def test_ui_reply_uses_persisted_sender_and_thread(api, gmail):
    tracked()
    store.put(
        "inbox",
        "incoming",
        {
            "mailbox": "sender@example.test",
            "sender": "owner@example.test",
            "subject": "Re: Website",
            "thread_id": "thread-1",
            "rfc_message_id": "<incoming@test>",
            "conversation_purpose": "reply",
        },
    )
    result = api.post(
        "/api/gmail/drafts",
        json={
            "recipient": "attacker@example.test",
            "body": "Reviewed reply",
            "purpose": "reply",
            "incoming_id": "incoming",
        },
    )
    assert result.status_code == 200
    assert result.json()["recipient_email"] == "owner@example.test"
    assert result.json()["provider_thread_id"] == "thread-1"


@pytest.mark.asyncio
async def test_newly_tracked_thread_is_backfilled_after_cursor_has_advanced(gmail):
    tracked()
    store.put(
        "gmail_cursor", "sender@example.test", {"history_id": "100", "thread_ids": []}
    )
    gmail.thread_data["thread-1"] = [raw_message()]
    assert (await process_inbox_batch())["recorded"] == 1
    assert store.get("gmail_cursor", "sender@example.test")["thread_ids"] == [
        "thread-1"
    ]


@pytest.mark.asyncio
async def test_inline_text_attachment_body_is_decoded(gmail):
    message = raw_message()
    message["payload"]["body"] = {"attachmentId": "inline-text"}
    gmail.messages_api.attachments = lambda: SimpleNamespace(
        get=lambda **kwargs: response({"data": encoded("Complete long message")})
    )
    parsed = await email_service.parse_full_message(message)
    assert parsed["body"] == "Complete long message"


def test_oidc_webhook_requires_verified_matching_service_identity(
    api, gmail, monkeypatch
):
    from routers import webhooks

    monkeypatch.setattr(
        settings, "PUBSUB_AUDIENCE", "https://agent.example.test/webhooks/gmail"
    )
    monkeypatch.setattr(
        settings, "PUBSUB_SERVICE_ACCOUNT_EMAIL", "push@example.iam.gserviceaccount.com"
    )
    data = {
        "message": {
            "data": encoded(
                json.dumps({"emailAddress": "sender@example.test", "historyId": "150"})
            )
        }
    }
    assert api.post("/webhooks/gmail", json=data).status_code == 403
    monkeypatch.setattr(
        webhooks,
        "verify_oidc",
        lambda token: {"email": "wrong@example.test", "email_verified": True},
    )
    assert (
        api.post(
            "/webhooks/gmail", json=data, headers={"Authorization": "Bearer fixture"}
        ).status_code
        == 403
    )
    monkeypatch.setattr(
        webhooks,
        "verify_oidc",
        lambda token: {
            "email": settings.PUBSUB_SERVICE_ACCOUNT_EMAIL,
            "email_verified": True,
        },
    )
    assert (
        api.post(
            "/webhooks/gmail", json=data, headers={"Authorization": "Bearer fixture"}
        ).status_code
        == 200
    )


def test_unknown_web_origin_cannot_read_local_gmail_controls(api):
    result = api.get(
        "/api/gmail/status", headers={"Origin": "https://unknown.example.test"}
    )
    assert "access-control-allow-origin" not in result.headers


def test_confirmation_is_atomic_and_idempotent():
    store.put("messages", "dispatch", {"status": "sending", "approval_id": "approval"})
    store.put("approvals", "approval", {"status": "sending", "dispatch_id": "dispatch"})
    store.confirm_submission("dispatch", "provider-id", "gmail-thread")
    store.confirm_submission("dispatch", "provider-id", "gmail-thread")
    assert store.get("messages", "dispatch")["status"] == "sent"
    assert store.get("approvals", "approval")["status"] == "sent"
    with pytest.raises(ConflictError):
        store.confirm_submission("dispatch", "different-id", "gmail-thread")
    assert store.get("approvals", "approval")["provider_message_id"] == "provider-id"
