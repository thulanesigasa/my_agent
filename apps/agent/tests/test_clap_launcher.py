import os
import sys
import numpy as np
import pytest

# Ensure apps/agent is in import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.clap_launcher import SingleOrDoubleClapDetector, ClapLauncher


def generate_audio_impulse(peak_amplitude: float = 0.8, length: int = 1024) -> np.ndarray:
    """Generates a synthetic audio block containing an impulse peak."""
    data = np.zeros(length, dtype=np.float32)
    data[10] = peak_amplitude
    data[11] = peak_amplitude * 0.5
    return data


def generate_silence(length: int = 1024) -> np.ndarray:
    """Generates a silent audio block."""
    return np.zeros(length, dtype=np.float32)


def test_single_clap_instant_trigger():
    detector = SingleOrDoubleClapDetector(single_clap=True, energy_threshold=0.18)
    clap_block = generate_audio_impulse(0.5)

    t0 = 1000.0
    res = detector.process_audio_chunk(clap_block, timestamp=t0)
    assert res is True


def test_double_clap_mode_requires_two_claps():
    detector = SingleOrDoubleClapDetector(single_clap=False, energy_threshold=0.25, min_clap_interval=0.15, max_clap_interval=0.75)
    clap_block = generate_audio_impulse(0.8)

    t0 = 1000.0
    # First clap
    res1 = detector.process_audio_chunk(clap_block, timestamp=t0)
    assert res1 is False

    detector.process_audio_chunk(generate_silence(), timestamp=t0 + 0.05)

    # Second clap
    t1 = t0 + 0.35
    res2 = detector.process_audio_chunk(clap_block, timestamp=t1)
    assert res2 is True


def test_refractory_period_blocks_multitrigger():
    detector = SingleOrDoubleClapDetector(single_clap=True, refractory_period=2.0)
    detector.last_trigger_time = 1000.0

    clap_block = generate_audio_impulse(0.8)
    res = detector.process_audio_chunk(clap_block, timestamp=1001.0)
    assert res is False
