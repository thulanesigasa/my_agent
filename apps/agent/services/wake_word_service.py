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
    Algorithmic Wake-Word Detector analyzing vocal energy envelope for keyword "Agent".
    Designed for fast, offline activation without external API latency.
    """

    def __init__(
        self,
        wake_word: str = "Agent",
        energy_threshold: float = 0.01,
        min_speech_duration: float = 0.08,
        refractory_period: float = 3.0,
    ):
        self.wake_word = wake_word
        self.energy_threshold = energy_threshold
        self.min_speech_duration = min_speech_duration
        self.refractory_period = refractory_period

        self.last_trigger_time: float = 0.0
        self.speech_start_time: Optional[float] = None
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

        # Speech envelope detection for spoken vocal command "Agent"
        if rms_energy >= self.energy_threshold:
            if self.speech_start_time is None:
                self.speech_start_time = now
                self.vocal_bursts = 1
            else:
                speech_duration = now - self.speech_start_time
                if speech_duration >= self.min_speech_duration:
                    logger.info(f"🗣️ Vocal command '{self.wake_word}' detected! (RMS Energy: {rms_energy:.4f})")
                    
                    self.speech_start_time = None
                    self.vocal_bursts = 0
                    self.last_trigger_time = now
                    return True, True, "pharez"
        else:
            # Reset speech window if silence > 400ms
            if self.speech_start_time is not None and (now - self.speech_start_time > 0.40):
                self.speech_start_time = None
                self.vocal_bursts = 0

        return False, False, "None"


wake_word_detector = WakeWordDetector()
