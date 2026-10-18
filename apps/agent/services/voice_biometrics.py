"""
Voice Biometrics & Speaker Identification Service.

Uses spectral feature extraction (MFCC approximation, spectral centroid, spectral energy roll-off)
to extract voice embeddings from PCM audio streams and match against registered user profiles (e.g., Pharez / Thulane).
"""

import json
import logging
import os
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("agent.voice_biometrics")


def get_voice_profiles_dir() -> Path:
    """Returns directory path for storing enrolled speaker voice profiles."""
    from tools.procedural_tools import get_memory_dir
    mem_dir = get_memory_dir()
    profiles_dir = mem_dir / "voice_profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir


class VoiceBiometricsService:
    """
    Asynchronous Voice Biometrics & Feature Extractor:
    - Computes spectral feature vectors (MFCC / Spectral Centroid / Energy distribution) from audio arrays.
    - Enrolls new speaker profiles.
    - Verifies speaker identity against stored voice profile embeddings.
    """

    def __init__(self, sample_rate: int = 16000, n_fft: int = 512, n_mfcc: int = 13):
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.n_mfcc = n_mfcc
        self._ensure_default_admin_profile()

    def extract_features(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Extracts normalized spectral feature vector (13-dim MFCC approximation + spectral centroid & energy)
        from a float32 / int16 numpy array.
        """
        if audio_data.dtype != np.float32:
            if np.issubdtype(audio_data.dtype, np.integer):
                max_int = float(np.iinfo(audio_data.dtype).max)
                audio_data = audio_data.astype(np.float32) / max_int

        if len(audio_data) < 256:
            return np.zeros(self.n_mfcc + 2, dtype=np.float32)

        # Windowing & FFT spectrum
        windowed = audio_data[:self.n_fft] * np.hanning(min(len(audio_data), self.n_fft))
        spectrum = np.abs(np.fft.rfft(windowed, n=self.n_fft))
        spectrum = np.maximum(spectrum, 1e-9)

        # Log power spectrum
        log_spectrum = np.log(spectrum)

        # Discrete Cosine Transform (DCT) for MFCC approximation
        mfccs = []
        num_freq_bins = len(log_spectrum)
        for i in range(self.n_mfcc):
            basis = np.cos(np.pi * i * (np.arange(num_freq_bins) + 0.5) / num_freq_bins)
            mfcc_val = float(np.sum(log_spectrum * basis))
            mfccs.append(mfcc_val)

        # Spectral Centroid
        freqs = np.fft.rfftfreq(self.n_fft, d=1.0 / self.sample_rate)
        centroid = float(np.sum(freqs * spectrum) / np.sum(spectrum))

        # Total Spectral Energy
        energy = float(np.sum(audio_data ** 2) / len(audio_data))

        feature_vector = np.array(mfccs + [centroid, energy], dtype=np.float32)

        # L2 Normalization
        norm = np.linalg.norm(feature_vector)
        if norm > 0:
            feature_vector /= norm

        return feature_vector

    def enroll_speaker(self, speaker_id: str, audio_data: np.ndarray, display_name: str = "Pharez") -> Dict[str, Any]:
        """
        Enrolls a speaker voice profile into memory/voice_profiles/<speaker_id>.json.
        """
        feature_vector = self.extract_features(audio_data)
        profiles_dir = get_voice_profiles_dir()
        profile_path = profiles_dir / f"{speaker_id.lower()}.json"

        profile_data = {
            "speaker_id": speaker_id.lower(),
            "display_name": display_name,
            "feature_vector": feature_vector.tolist(),
            "sample_rate": self.sample_rate,
            "enrolled_at": os.getenv("CURRENT_TIME", "2026-08-11")
        }

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2)

        logger.info(f"Enrolled speaker voice profile: '{display_name}' ({speaker_id}) at {profile_path}")
        return profile_data

    def verify_speaker(
        self, audio_data: np.ndarray, target_speaker_id: str = "pharez", match_threshold: float = 0.70
    ) -> Tuple[bool, float, str]:
        """
        Verifies if incoming audio features match the target speaker profile.
        Returns: (is_matched: bool, similarity_score: float, display_name: str)
        """
        profiles_dir = get_voice_profiles_dir()
        profile_path = profiles_dir / f"{target_speaker_id.lower()}.json"

        if not profile_path.exists():
            # If target missing, fallback to default admin
            profile_path = profiles_dir / "pharez.json"
            if not profile_path.exists():
                return False, 0.0, "Unknown"

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                profile_data = json.load(f)

            enrolled_vector = np.array(profile_data.get("feature_vector", []), dtype=np.float32)
            display_name = profile_data.get("display_name", target_speaker_id)

            if len(enrolled_vector) == 0:
                return False, 0.0, display_name

            incoming_vector = self.extract_features(audio_data)

            # Cosine similarity
            dot_prod = float(np.dot(incoming_vector, enrolled_vector))
            norm_in = float(np.linalg.norm(incoming_vector))
            norm_en = float(np.linalg.norm(enrolled_vector))

            if norm_in > 0 and norm_en > 0:
                similarity = dot_prod / (norm_in * norm_en)
            else:
                similarity = 0.0

            # Dynamic score scaling (range 0.0 to 1.0)
            similarity_score = max(0.0, min(1.0, float((similarity + 1.0) / 2.0)))
            is_matched = similarity_score >= match_threshold

            logger.info(f"Voice verification for '{display_name}': Score={similarity_score:.3f}, Match={is_matched}")
            return is_matched, similarity_score, display_name

        except Exception as e:
            logger.error(f"Error in speaker verification: {e}")
            return False, 0.0, "Unknown"

    def _ensure_default_admin_profile(self):
        """Initializes default admin voice profile for Pharez if missing."""
        profiles_dir = get_voice_profiles_dir()
        profile_path = profiles_dir / "pharez.json"

        if not profile_path.exists():
            # Generate baseline reference vector for admin
            np.random.seed(42)
            dummy_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, self.sample_rate), dtype=np.float32)
            self.enroll_speaker(speaker_id="pharez", audio_data=dummy_audio, display_name="Pharez (T.s Industries)")


voice_biometrics_service = VoiceBiometricsService()
