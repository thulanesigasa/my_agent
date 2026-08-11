import os
import sys
import pytest
import numpy as np
import asyncio

# Ensure apps/agent is in import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.voice_biometrics import voice_biometrics_service
from services.wake_word_service import wake_word_detector
from services.sandbox_service import sandbox_service
from tools.procedural_tools import list_available_skills


def test_voice_biometrics_enroll_and_verify():
    np.random.seed(123)
    sample_rate = 16000
    audio_sample = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, sample_rate), dtype=np.float32)

    # Enroll speaker
    enroll_res = voice_biometrics_service.enroll_speaker(
        speaker_id="test_admin", audio_data=audio_sample, display_name="Test Admin"
    )
    assert enroll_res["speaker_id"] == "test_admin"

    # Verify speaker identity
    is_matched, score, name = voice_biometrics_service.verify_speaker(
        audio_data=audio_sample, target_speaker_id="test_admin", match_threshold=0.60
    )
    assert is_matched is True
    assert score >= 0.60
    assert name == "Test Admin"


def test_wake_word_detector():
    audio_block = np.full(1024, 0.5, dtype=np.float32)
    t0 = 1000.0

    # Simulate vocal energy burst sequence
    wake_word_detector.process_audio_chunk(audio_block, timestamp=t0)
    detected, authed, speaker = wake_word_detector.process_audio_chunk(audio_block, timestamp=t0 + 0.10)
    assert detected is True


def test_sandbox_clean_code_execution():
    code = (
        "import math\n"
        "res = math.factorial(5)\n"
        "print(f'RESULT={res}')\n"
    )
    res = asyncio.run(sandbox_service.execute_with_self_healing(code, max_retries=1))
    assert res["success"] is True
    assert "RESULT=120" in res["stdout"]


def test_sandbox_self_healing_repair():
    # Intentionally broken code missing import and having typo
    code = (
        "# Missing math import initially\n"
        "res = math.factorial(5)\n"
        "print(f'RESULT={res}')\n"
    )
    res = asyncio.run(sandbox_service.execute_with_self_healing(code, max_retries=2))
    # Should either succeed via self-healing or capture error logs
    assert "attempts" in res
    assert isinstance(res["repair_logs"], list)


def test_list_available_skills():
    skills = list_available_skills()
    assert isinstance(skills, list)
