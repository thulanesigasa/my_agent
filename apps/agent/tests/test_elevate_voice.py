"""Wake activation, real transcription failures and isolated voice sessions."""

import json
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient
from config import settings
from core.store import store
from services.audio_service import AudioService, TranscriptionUnavailable
from services.wake_word_service import WakeWordDetector
from services.clap_launcher import ClapLauncher
from services import automation as auto
from services.email_service import email_service
from test_automation_phase6 import enable, allow_next_tick


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Agent", False),
        ("agen", False),
        ("Hey Agent", False),
        ("elevate agency", False),
        ("elevate agen", False),
        ("elevate agent", True),
        ("Elevate agent", True),
        ("please elevate agent", True),
    ],
)
def test_full_wake_phrase_required_and_not_an_authentication_claim(text, expected):
    detected, authenticated, _ = WakeWordDetector().process_transcript(text, 1000)
    assert detected == expected
    assert authenticated is False


def test_pcm_loudness_alone_does_not_activate_and_clap_launcher_defaults_to_double():
    detector = WakeWordDetector()
    assert (
        detector.process_audio_chunk(np.ones(1024, dtype=np.float32), 1000)[0] is False
    )
    assert (
        detector.process_audio_chunk(np.ones(1024, dtype=np.float32), 1001)[0] is False
    )
    assert ClapLauncher().detector.single_clap is False


def test_optional_recognizer_uses_words_and_cooldown():
    class Recognizer:
        def AcceptWaveform(self, pcm):
            assert isinstance(pcm, bytes) and pcm
            return True

        def Result(self):
            return json.dumps({"text": "elevate agent"})

    detector = WakeWordDetector(recognizer=Recognizer())
    block = np.ones(2048, dtype=np.float32) * 0.1
    assert detector.process_audio_chunk(block, 1000)[0]
    assert not detector.process_audio_chunk(block, 1001)[0]
    assert detector.process_audio_chunk(block, 1004)[0]


@pytest.mark.asyncio
async def test_missing_transcription_provider_never_returns_an_invented_command(
    monkeypatch,
):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    with pytest.raises(TranscriptionUnavailable, match="not configured"):
        await AudioService.transcribe_audio_bytes(b"x" * 200)
    assert await AudioService.transcribe_audio_bytes(b"") == ""


def test_websocket_transcription_failure_never_invokes_workflow(monkeypatch):
    from main import app
    import main

    invoke = AsyncMock()
    monkeypatch.setattr(main.agent_workflow, "ainvoke", invoke)
    monkeypatch.setattr(
        main.audio_service,
        "transcribe_audio_bytes",
        AsyncMock(
            side_effect=TranscriptionUnavailable(
                "Speech recognition failed. No command was submitted."
            )
        ),
    )
    with TestClient(app) as api, api.websocket_connect("/ws/audio") as ws:
        ws.send_bytes(b"x" * 200)
        assert ws.receive_json()["state"] == "processing"
        error = ws.receive_json()
        assert error["type"] == "error" and "No command" in error["message"]
    invoke.assert_not_awaited()


def test_server_voice_uses_configured_chat_thread_and_isolates_unconfigured_connections(
    monkeypatch,
):
    from main import app
    import main

    invoke = AsyncMock(return_value={"final_output": "Hello from your team"})
    monkeypatch.setattr(main.agent_workflow, "ainvoke", invoke)
    monkeypatch.setattr(main, "schedule_background_learning", lambda state: None)
    monkeypatch.setattr(
        main.audio_service,
        "transcribe_audio_bytes",
        AsyncMock(return_value="Show my status"),
    )
    monkeypatch.setattr(
        main.audio_service,
        "synthesize_speech_bytes",
        AsyncMock(return_value=b"fake-audio"),
    )
    with TestClient(app) as api:
        ids = []
        for configured in ["project_manager_same_chat", None, None]:
            with api.websocket_connect("/ws/audio") as ws:
                if configured:
                    ws.send_json({"type": "configure", "thread_id": configured})
                ws.send_bytes(b"x" * 200)
                for _ in range(8):
                    item = ws.receive()
                    if (
                        item.get("text")
                        and json.loads(item["text"]).get("state") == "idle"
                    ):
                        break
            ids.append(invoke.call_args.kwargs["config"]["configurable"]["thread_id"])
    assert ids[0] == "project_manager_same_chat"
    assert ids[1] != ids[2]


@pytest.mark.asyncio
async def test_three_repeated_coordinator_failures_pause_but_first_two_retry(
    monkeypatch,
):
    enable()
    monkeypatch.setattr(auto, "process_inbox_batch", AsyncMock(return_value={}))
    monkeypatch.setattr(
        auto,
        "generate_weekly_report",
        AsyncMock(side_effect=RuntimeError("Local failure")),
    )
    for count in range(1, 4):
        runtime = store.get("automation_runtime", email_service.expected_email) or {}
        store.put(
            "automation_runtime",
            email_service.expected_email,
            {**runtime, "next_tick_at": "2020-01-01T00:00:00+00:00"},
        )
        with pytest.raises(RuntimeError):
            await auto.tick()
        assert auto.config(email_service.expected_email)["paused"] == (count == 3)
        assert (
            store.get("automation_runtime", email_service.expected_email)[
                "consecutive_failures"
            ]
            == count
        )


@pytest.mark.asyncio
async def test_uncertain_sends_get_bounded_provider_reconciliation_never_resend(
    monkeypatch,
):
    enable()
    mailbox = email_service.expected_email
    old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    for i in range(3):
        with store.connect() as db:
            db.execute(
                "INSERT INTO records VALUES (?,?,?)",
                (
                    "approvals",
                    f"held-{i}",
                    json.dumps(
                        {
                            "id": f"held-{i}",
                            "status": "delivery_unknown",
                            "sender_mailbox": mailbox,
                            "updated_at": old,
                        }
                    ),
                ),
            )
    reconcile = AsyncMock(return_value={"status": "held"})
    send = AsyncMock(side_effect=AssertionError("Never resend"))
    monkeypatch.setattr(email_service, "reconcile", reconcile)
    monkeypatch.setattr(email_service, "send_email", send)
    monkeypatch.setattr(auto, "process_inbox_batch", AsyncMock(return_value={}))
    result = await auto.tick()
    assert reconcile.await_count == 2
    assert len([r for r in result["results"] if r["stage"] == "reconciliation"]) == 2
    allow_next_tick()
    await auto.tick()
    assert reconcile.await_count == 3  # First two wait at least 15 minutes.
    assert all(a["status"] == "delivery_unknown" for a in store.list("approvals"))
    send.assert_not_awaited()
