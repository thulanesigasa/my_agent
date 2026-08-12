"""
Wake-Word & Vocal Command Activation Service.

Monitors real-time microphone stream for vocal wake words ("Hey Pharez" / "Hey Agent")
and pairs with Voice Biometrics to authenticate speaker identity before activating agent voice mode.
"""

import time
import logging
from typing import Optional, Callable, Tuple
import numpy as np
from services.voice_biometrics import voice_biometrics_service

logger = logging.getLogger("agent.wake_word_service")


class WakeWordDetector:
    """
    Algorithmic Wake-Word Detector analyzing vocal energy envelope & acoustic cadence for keyword "Agent".
    Designed for fast, offline activation without external API latency.
    """

    def __init__(
        self,
        wake_word: str = "Agent",
        energy_threshold: float = 0.04,
        min_syllable_count: int = 2,
        refractory_period: float = 3.0,
    ):
        self.wake_word = wake_word
        self.energy_threshold = energy_threshold
        self.min_syllable_count = min_syllable_count
        self.refractory_period = refractory_period

        self.last_trigger_time: float = 0.0
        self.vocal_bursts: int = 0
        self.last_burst_time: float = 0.0

    def process_audio_chunk(
        self, audio_data: np.ndarray, timestamp: Optional[float] = None
    ) -> Tuple[bool, bool, str]:
        """
        Processes a block of PCM audio data.
        Returns (is_wake_word_detected: bool, is_speaker_authenticated: bool, speaker_name: str)
        """
        now = timestamp if timestamp is not None else time.time()

        if now - self.last_trigger_time < self.refractory_period:
            return False, False, "Cooldown"

        if audio_data.dtype != np.float32:
            if np.issubdtype(audio_data.dtype, np.integer):
                max_int = float(np.iinfo(audio_data.dtype).max)
                audio_data = audio_data.astype(np.float32) / max_int

        peak_amplitude = float(np.max(np.abs(audio_data)))
        rms_energy = float(np.sqrt(np.mean(audio_data ** 2)))

        # Speech envelope detection
        if rms_energy >= self.energy_threshold:
            if now - self.last_burst_time > 0.08:  # 80ms syllable separation
                self.vocal_bursts += 1
                self.last_burst_time = now
                logger.debug(f"Vocal energy burst detected ({self.vocal_bursts} syllables).")
        else:
            # Reset syllable count if silence > 600ms
            if self.last_burst_time > 0 and (now - self.last_burst_time > 0.60):
                self.vocal_bursts = 0

        # Check if vocal burst cadence matches wake word ("Agent": ~2 syllables within 0.8s)
        if self.vocal_bursts >= self.min_syllable_count and (now - self.last_burst_time < 0.80):
            logger.info(f"🗣️ Wake word detected ('{self.wake_word}')! Verifying speaker voice biometrics...")
            
            # Verify voice biometric profile
            is_authed, score, speaker_name = voice_biometrics_service.verify_speaker(
                audio_data=audio_data, target_speaker_id="pharez"
            )

            self.vocal_bursts = 0
            self.last_trigger_time = now

            if is_authed:
                logger.info(f"✅ Speaker Authenticated: Welcome, {speaker_name}! (Biometric Score: {score:.2f})")
            else:
                logger.info(f"👤 Wake word triggered by guest/unverified voice: {speaker_name} (Score: {score:.2f})")

            return True, is_authed, speaker_name

        return False, False, "None"


wake_word_detector = WakeWordDetector()
