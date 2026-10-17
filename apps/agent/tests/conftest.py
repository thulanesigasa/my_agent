"""Offline tests: temporary databases and explicitly requested fake providers."""

import os
import sys
from pathlib import Path
import tempfile

# Never use a developer's credentials or durable runtime data in the test suite.
for name in (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "TAVILY_API_KEY",
    "GMAIL_USER_EMAIL",
    "PUBSUB_AUDIENCE",
    "PUBSUB_SERVICE_ACCOUNT_EMAIL",
    "GMAIL_CLIENT_ID",
    "GMAIL_CLIENT_SECRET",
    "GMAIL_REFRESH_TOKEN",
    "WEBHOOK_SECRET",
    "LANGSMITH_API_KEY",
    "LANGCHAIN_API_KEY",
):
    os.environ[name] = ""
os.environ["GMAIL_TOKEN_PATH"] = str(
    Path(tempfile.mkdtemp(prefix="agent-test-oauth-")) / "absent.json"
)
os.environ["GMAIL_DRAFT_REPLIES"] = "false"
os.environ["ENV"] = "test"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["WEEKLY_REPORTS_ENABLED"] = "false"
os.environ["ALLOW_TAVILY_RESEARCH"] = "false"
os.environ["RESEARCH_JOBS_ENABLED"] = "false"
os.environ["TAVILY_DAILY_QUERY_LIMIT"] = "5"
os.environ["TAVILY_MONTHLY_QUERY_LIMIT"] = "100"
os.environ["OSM_DAILY_QUERY_LIMIT"] = "20"
os.environ["OSM_PROVIDER"] = "private_coffee"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["STATE_DB_PATH"] = str(
    Path(tempfile.mkdtemp(prefix="agent-test-bootstrap-")) / "state.sqlite3"
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core.store import StateStore, store


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    path = str(tmp_path / "agent.sqlite3")
    StateStore(path)
    monkeypatch.setattr(store, "path", path)
    from config import settings

    monkeypatch.setattr(settings, "STATE_DB_PATH", path)
    from services.email_service import email_service

    monkeypatch.setattr(email_service, "client", None)
    monkeypatch.setattr(email_service, "expected_email", "sender@example.test")
    return store


@pytest.fixture
def fake_llm(monkeypatch):
    from services.llm_factory import llm_factory

    async def triage(prompt, system_override=None):
        return '{"intent": "client_inquiry", "needs_human_approval": true}'

    async def draft(prompt, system_override=None):
        return "Thank you for your enquiry. Could you share your website requirements so we can discuss the scope?"

    monkeypatch.setattr(llm_factory, "invoke_triage", triage)
    monkeypatch.setattr(llm_factory, "invoke_drafter", draft)


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    import socket

    connect = socket.socket.connect

    def local_only(sock, address):
        if isinstance(address, tuple) and address[0] not in (
            "127.0.0.1",
            "::1",
            "localhost",
        ):
            raise AssertionError("External network access is disabled in tests")
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", local_only)


@pytest.fixture(autouse=True)
def temporary_voice_profiles(tmp_path, monkeypatch):
    from services import voice_biometrics

    profiles = tmp_path / "voice_profiles"
    profiles.mkdir()
    monkeypatch.setattr(voice_biometrics, "get_voice_profiles_dir", lambda: profiles)
