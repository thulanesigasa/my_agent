"""
Double-Clap Audio Trigger Service.

Listens to real-time host microphone input using `sounddevice` and `numpy`.
Detects two consecutive sharp clap sounds within a configurable timing window (150ms - 750ms),
then automatically ensures the FastAPI backend is running and opens the Web UI in the browser.
"""

import time
import logging
import os
import sys
import subprocess
import webbrowser
import urllib.request
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger("agent.clap_launcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class DoubleClapDetector:
    """
    Pure algorithmic double-clap detector operating on PCM audio chunks.
    Designed for testability without hardware microphone dependencies.
    """

    def __init__(
        self,
        energy_threshold: float = 0.25,
        min_clap_interval: float = 0.15,
        max_clap_interval: float = 0.75,
        refractory_period: float = 2.5,
    ):
        """
        :param energy_threshold: Minimum normalized peak amplitude (0.0 to 1.0) to register as a clap.
        :param min_clap_interval: Minimum time (seconds) between clap 1 and clap 2 (filters echoes/single clap duration).
        :param max_clap_interval: Maximum time (seconds) between clap 1 and clap 2 to qualify as a double clap.
        :param refractory_period: Cooldown time (seconds) after a successful double clap trigger to avoid multi-triggers.
        """
        self.energy_threshold = energy_threshold
        self.min_clap_interval = min_clap_interval
        self.max_clap_interval = max_clap_interval
        self.refractory_period = refractory_period

        self.last_clap_time: Optional[float] = None
        self.last_trigger_time: float = 0.0
        self.in_peak: bool = False

    def process_audio_chunk(self, audio_data: np.ndarray, timestamp: Optional[float] = None) -> bool:
        """
        Processes a block of PCM audio data (NumPy array).
        Returns True if a double-clap sequence is detected, False otherwise.
        """
        now = timestamp if timestamp is not None else time.time()

        # Enforce post-trigger refractory period
        if now - self.last_trigger_time < self.refractory_period:
            return False

        # Calculate peak absolute amplitude of the block
        if audio_data.dtype != np.float32:
            # Normalize integers to float range [-1.0, 1.0] if necessary
            if np.issubdtype(audio_data.dtype, np.integer):
                max_int = float(np.iinfo(audio_data.dtype).max)
                audio_data = audio_data.astype(np.float32) / max_int

        peak = float(np.max(np.abs(audio_data)))

        # Transient peak detection (rising edge above threshold)
        if peak >= self.energy_threshold:
            if not self.in_peak:
                self.in_peak = True
                return self._register_clap_peak(now)
        else:
            self.in_peak = False

        # Reset last clap time if user waited too long for the second clap
        if self.last_clap_time and (now - self.last_clap_time > self.max_clap_interval):
            logger.debug("Double clap window expired. Resetting clap state.")
            self.last_clap_time = None

        return False

    def _register_clap_peak(self, now: float) -> bool:
        """Helper to evaluate clap sequence timing on peak detection."""
        if self.last_clap_time is None:
            # First clap registered
            self.last_clap_time = now
            logger.info("👏 First clap detected! Waiting for second clap...")
            return False

        elapsed = now - self.last_clap_time

        if elapsed < self.min_clap_interval:
            # Too fast - likely same sound peak resonance or echo
            logger.debug(f"Clap sound too fast ({elapsed:.3f}s). Ignoring as echo.")
            return False

        if elapsed <= self.max_clap_interval:
            # Valid double clap!
            logger.info(f"👏 👏 Second clap detected ({elapsed:.3f}s after first)! Double clap confirmed!")
            self.last_clap_time = None
            self.last_trigger_time = now
            return True
        else:
            # Too slow - treat this peak as a new first clap
            logger.info("First clap timed out. Registering sound as new first clap...")
            self.last_clap_time = now
            return False


class ClapLauncher:
    """
    Service wrapper around DoubleClapDetector that interacts with system processes:
    Checks/boots FastAPI backend server and launches web browser interface.
    """

    def __init__(
        self,
        backend_url: str = "http://localhost:8000/health",
        frontend_url: str = "http://localhost:3000",
        backend_cmd: Optional[str] = None,
        detector: Optional[DoubleClapDetector] = None,
    ):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.backend_cmd = backend_cmd
        self.detector = detector or DoubleClapDetector()

    def is_backend_running(self) -> bool:
        """Check if backend HTTP health endpoint responds with 200 OK."""
        try:
            req = urllib.request.Request(self.backend_url, headers={"User-Agent": "ClapLauncher"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start_backend(self):
        """Spawns the FastAPI backend server in background if not already running."""
        if self.is_backend_running():
            logger.info("Backend service is already healthy and running.")
            return

        logger.info("Starting FastAPI backend server process...")
        if self.backend_cmd:
            cmd = self.backend_cmd
        else:
            # Default python module invocation for Uvicorn agent main
            cmd = f"{sys.executable} -m uvicorn apps.agent.main:app --host 0.0.0.0 --port 8000"

        # Determine agent directory root path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        agent_dir = os.path.abspath(os.path.join(current_dir, ".."))

        try:
            subprocess.Popen(
                cmd,
                shell=True,
                cwd=agent_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Backend process spawned successfully.")

            # Wait briefly for backend startup confirmation
            for _ in range(10):
                time.sleep(0.5)
                if self.is_backend_running():
                    logger.info("Backend health check succeeded!")
                    break
        except Exception as e:
            logger.error(f"Failed to spawn backend process: {e}")

    def open_browser(self):
        """Opens the Next.js web application frontend in the system browser."""
        logger.info(f"Opening web browser at {self.frontend_url}...")
        try:
            webbrowser.open(self.frontend_url)
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")

    def trigger_action(self):
        """Execute complete kick-start action sequence on double-clap detection."""
        logger.info("🚀 TRIGGER ACTIVATED: Kick-starting backend and opening web browser!")
        self.start_backend()
        self.open_browser()

    def listen(self, sample_rate: int = 44100, block_size: int = 2048):
        """
        Starts audio input streaming from default system microphone using sounddevice.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("`sounddevice` package is required for real-time audio input.")
            logger.error("Please install dependencies: pip install sounddevice")
            sys.exit(1)

        def audio_callback(indata: np.ndarray, frames: int, time_info, status):
            if status:
                logger.warning(f"Audio status warning: {status}")
            
            # Mono channel peak extraction
            mono_data = indata[:, 0] if indata.ndim > 1 else indata
            if self.detector.process_audio_chunk(mono_data):
                self.trigger_action()

        logger.info(f"Listening for double claps on default microphone (sample_rate={sample_rate})...")
        logger.info("Clap hands TWICE quickly to kick-start backend and open web browser. Press Ctrl+C to exit.")

        try:
            with sd.InputStream(
                callback=audio_callback,
                channels=1,
                samplerate=sample_rate,
                blocksize=block_size,
                dtype="float32",
            ):
                while True:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Stopped clap listener.")
        except Exception as e:
            logger.error(f"Microphone audio streaming error: {e}")


if __name__ == "__main__":
    launcher = ClapLauncher()
    launcher.listen()
