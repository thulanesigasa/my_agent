"""Recognize 'elevate agent' from transcripts or an optional local Vosk model.

Sound energy is not a keyword and a wake phrase is not speaker authentication.
"""

import json
import logging
import re
import time
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger("agent.wake_word_service")


class WakeWordDetector:
    def __init__(
        self, wake_word="elevate agent", refractory_period=3.0, recognizer=None
    ):
        self.wake_word = wake_word
        self.refractory_period = refractory_period
        self.last_trigger_time = float("-inf")
        self.recognizer = recognizer
        self.sample_rate = 44100
        self.model = None

    def configure(self, model_path: str, sample_rate: int = 44100) -> bool:
        """Load a user-installed local model once; never download or bill a provider."""
        try:
            from vosk import Model, KaldiRecognizer

            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(
                self.model,
                16000,
                json.dumps(["elevate agent", "[unk]"]),
            )
            self.sample_rate = sample_rate
            return True
        except Exception as exc:
            logger.warning(
                "Offline wake recognition unavailable (%s); double claps remain available",
                type(exc).__name__,
            )
            self.recognizer = None
            return False

    def process_transcript(
        self, text: str, timestamp: Optional[float] = None
    ) -> Tuple[bool, bool, str]:
        stamp = timestamp if timestamp is not None else time.time()
        words = " ".join(re.findall(r"\w+", str(text).casefold()))
        phrase = re.escape(self.wake_word.casefold()).replace(r"\ ", r"\s+")
        pattern = r"\b" + phrase + r"\b"
        if stamp - self.last_trigger_time < self.refractory_period or not re.search(
            pattern, words
        ):
            return False, False, "None"
        self.last_trigger_time = stamp
        return True, False, "Unverified speaker"

    def process_audio_chunk(
        self, audio_data: np.ndarray, timestamp: Optional[float] = None
    ) -> Tuple[bool, bool, str]:
        if self.recognizer is None or audio_data.size == 0:
            return False, False, "Recognition unavailable"
        audio = np.asarray(audio_data)
        if np.issubdtype(audio.dtype, np.integer):
            audio = audio.astype(np.float32) / float(np.iinfo(audio.dtype).max)
        audio = np.nan_to_num(audio.astype(np.float32))
        if self.sample_rate != 16000:
            size = max(1, round(len(audio) * 16000 / self.sample_rate))
            audio = np.interp(
                np.linspace(0, len(audio) - 1, size), np.arange(len(audio)), audio
            )
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
        try:
            if self.recognizer.AcceptWaveform(pcm):
                return self.process_transcript(
                    json.loads(self.recognizer.Result()).get("text", ""), timestamp
                )
        except Exception as exc:
            logger.warning("Wake recognition failed (%s)", type(exc).__name__)
        return False, False, "None"


wake_word_detector = WakeWordDetector()
