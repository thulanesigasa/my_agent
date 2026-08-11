import os
import sys
import numpy as np
import pytest

# Ensure apps/agent is in import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.clap_launcher import DoubleClapDetector, ClapLauncher


def generate_audio_impulse(peak_amplitude: float = 0.8, length: int = 1024) -> np.ndarray:
    """Generates a synthetic audio block containing an impulse peak."""
    data = np.zeros(length, dtype=np.float32)
    data[10] = peak_amplitude
    data[11] = peak_amplitude * 0.5
    return data


def generate_silence(length: int = 1024) -> np.ndarray:
    """Generates a silent audio block."""
    return np.zeros(length, dtype=np.float32)


def test_single_clap_does_not_trigger():
    detector = DoubleClapDetector(energy_threshold=0.3)
    clap_block = generate_audio_impulse(0.8)

    t0 = 1000.0
    res = detector.process_audio_chunk(clap_block, timestamp=t0)
    assert res is False
    assert detector.last_clap_time == t0


def test_valid_double_clap_triggers():
    detector = DoubleClapDetector(energy_threshold=0.3, min_clap_interval=0.15, max_clap_interval=0.75)
    clap_block = generate_audio_impulse(0.8)

    t0 = 1000.0
    # First clap
    res1 = detector.process_audio_chunk(clap_block, timestamp=t0)
    assert res1 is False

    # Reset in_peak state with quiet block
    detector.process_audio_chunk(generate_silence(), timestamp=t0 + 0.05)

    # Second clap at 0.35s after first clap
    t1 = t0 + 0.35
    res2 = detector.process_audio_chunk(clap_block, timestamp=t1)
    assert res2 is True


def test_clap_echo_too_fast_is_ignored():
    detector = DoubleClapDetector(energy_threshold=0.3, min_clap_interval=0.15)
    clap_block = generate_audio_impulse(0.8)

    t0 = 1000.0
    detector.process_audio_chunk(clap_block, timestamp=t0)
    detector.process_audio_chunk(generate_silence(), timestamp=t0 + 0.02)

    # Echo at 0.05s (< 0.15s)
    res_echo = detector.process_audio_chunk(clap_block, timestamp=t0 + 0.05)
    assert res_echo is False


def test_clap_timeout_resets_state():
    detector = DoubleClapDetector(energy_threshold=0.3, max_clap_interval=0.75)
    clap_block = generate_audio_impulse(0.8)

    t0 = 1000.0
    detector.process_audio_chunk(clap_block, timestamp=t0)

    # Silence for 1 second (past max_clap_interval)
    res_silence = detector.process_audio_chunk(generate_silence(), timestamp=t0 + 1.0)
    assert res_silence is False
    assert detector.last_clap_time is None


def test_refractory_period_blocks_multitrigger():
    detector = DoubleClapDetector(refractory_period=2.0)
    detector.last_trigger_time = 1000.0

    clap_block = generate_audio_impulse(0.8)
    # Attempting clap during refractory period
    res = detector.process_audio_chunk(clap_block, timestamp=1001.0)
    assert res is False
