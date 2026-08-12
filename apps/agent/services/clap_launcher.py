"""
Clap Audio Trigger & Auto-Launcher Service.

Listens to real-time host microphone input using `sounddevice` and `numpy`.
Detects sharp clap sounds (single clap or double clap) and automatically:
1. Boots the FastAPI backend server (port 8000) if unstarted.
2. Boots the Next.js web frontend dev server (port 3000) if unstarted.
3. Instantly launches the browser pointing to http://localhost:3000.
"""

import time
import logging
import os
import sys
import subprocess
import webbrowser
import urllib.request
import threading
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger("agent.clap_launcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class SingleOrDoubleClapDetector:
    """
    Pure algorithmic clap detector operating on PCM audio chunks.
    Supports instant single-clap activation or double-clap pattern matching.
    """

    def __init__(
        self,
        energy_threshold: float = 0.18,
        single_clap: bool = True,
        min_clap_interval: float = 0.12,
        max_clap_interval: float = 0.75,
        refractory_period: float = 2.5,
    ):
        """
        :param energy_threshold: Minimum normalized peak amplitude (0.0 to 1.0) to register as a clap.
        :param single_clap: If True, activates instantly on a single sharp clap. If False, requires double clap.
        :param min_clap_interval: Minimum time (seconds) between clap 1 and clap 2 for double clap mode.
        :param max_clap_interval: Maximum time (seconds) between clap 1 and clap 2 for double clap mode.
        :param refractory_period: Cooldown time (seconds) after a successful trigger to avoid multi-triggers.
        """
        self.energy_threshold = energy_threshold
        self.single_clap = single_clap
        self.min_clap_interval = min_clap_interval
        self.max_clap_interval = max_clap_interval
        self.refractory_period = refractory_period

        self.last_clap_time: Optional[float] = None
        self.last_trigger_time: float = 0.0
        self.in_peak: bool = False

    def process_audio_chunk(self, audio_data: np.ndarray, timestamp: Optional[float] = None) -> bool:
        """
        Processes a block of PCM audio data (NumPy array).
        Returns True if a clap activation condition is met, False otherwise.
        """
        now = timestamp if timestamp is not None else time.time()

        # Enforce post-trigger refractory period
        if now - self.last_trigger_time < self.refractory_period:
            return False

        # Normalize audio format if necessary
        if audio_data.dtype != np.float32:
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

        # Reset double clap timer if expired
        if not self.single_clap and self.last_clap_time and (now - self.last_clap_time > self.max_clap_interval):
            self.last_clap_time = None

        return False

    def _register_clap_peak(self, now: float) -> bool:
        """Helper to evaluate clap sequence timing on peak detection."""
        if self.single_clap:
            logger.info("👏 Single clap sound detected! Instant activation triggered!")
            self.last_trigger_time = now
            return True

        # Double clap logic
        if self.last_clap_time is None:
            self.last_clap_time = now
            logger.info("👏 First clap detected! Waiting for second clap...")
            return False

        elapsed = now - self.last_clap_time

        if elapsed < self.min_clap_interval:
            logger.debug(f"Clap sound too fast ({elapsed:.3f}s). Ignoring echo.")
            return False

        if elapsed <= self.max_clap_interval:
            logger.info(f"👏 👏 Second clap detected ({elapsed:.3f}s after first)! Double clap confirmed!")
            self.last_clap_time = None
            self.last_trigger_time = now
            return True
        else:
            logger.info("First clap timed out. Registering sound as new first clap...")
            self.last_clap_time = now
            return False


# Backwards compatibility alias
DoubleClapDetector = SingleOrDoubleClapDetector


class ClapLauncher:
    """
    Service wrapper around SingleOrDoubleClapDetector that interacts with system processes:
    Checks/boots FastAPI backend server AND Next.js web frontend, then instantly opens browser.
    """

    def __init__(
        self,
        backend_url: str = "http://localhost:8000/health",
        frontend_url: str = "http://localhost:3000",
        backend_cmd: Optional[str] = None,
        frontend_cmd: Optional[str] = None,
        detector: Optional[SingleOrDoubleClapDetector] = None,
    ):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.backend_cmd = backend_cmd
        self.frontend_cmd = frontend_cmd
        self.detector = detector or SingleOrDoubleClapDetector(single_clap=True, energy_threshold=0.18)

    def is_backend_running(self) -> bool:
        """Check if backend HTTP health endpoint responds with 200 OK."""
        try:
            req = urllib.request.Request(self.backend_url, headers={"User-Agent": "ClapLauncher"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def is_frontend_running(self) -> bool:
        """Check if Next.js frontend dev server responds on port 3000."""
        try:
            req = urllib.request.Request(self.frontend_url, headers={"User-Agent": "ClapLauncher"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status in (200, 304, 404)
        except Exception:
            return False

    def start_backend_async(self):
        """Spawns FastAPI backend server process in background."""
        if self.is_backend_running():
            logger.info("Backend service is already healthy and running (port 8000).")
            return

        logger.info("Starting FastAPI backend server process...")
        if self.backend_cmd:
            cmd = self.backend_cmd
        else:
            cmd = f"{sys.executable} -m uvicorn apps.agent.main:app --host 0.0.0.0 --port 8000"

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
            logger.info("Backend process spawned asynchronously.")
        except Exception as e:
            logger.error(f"Failed to spawn backend process: {e}")

    def start_frontend_async(self):
        """Spawns Next.js web frontend dev server process in background."""
        if self.is_frontend_running():
            logger.info("Web frontend service is already running (port 3000).")
            return

        logger.info("Starting Next.js web application frontend server (npm run dev)...")
        if self.frontend_cmd:
            cmd = self.frontend_cmd
        else:
            cmd = "npm run dev"

        current_dir = os.path.dirname(os.path.abspath(__file__))
        web_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "web"))

        try:
            subprocess.Popen(
                cmd,
                shell=True,
                cwd=web_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Next.js frontend process spawned asynchronously.")
        except Exception as e:
            logger.error(f"Failed to spawn frontend process: {e}")

    def open_browser_immediately(self):
        """Instantly launches web browser pointing to Next.js dashboard."""
        logger.info(f"🚀 INSTANT LAUNCH: Opening browser at {self.frontend_url}...")
        try:
            webbrowser.open(self.frontend_url)
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")

    def trigger_action(self):
        """Executes non-blocking parallel kick-start sequence on clap detection."""
        logger.info("👏 CLAP ACTIVATION CONFIRMED: Booting backend, web frontend, and opening browser!")
        
        # Spawn backend and frontend processes in parallel background threads
        t1 = threading.Thread(target=self.start_backend_async, daemon=True)
        t2 = threading.Thread(target=self.start_frontend_async, daemon=True)
        t1.start()
        t2.start()

        # Instantly open web browser without blocking!
        self.open_browser_immediately()

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
            
            mono_data = indata[:, 0] if indata.ndim > 1 else indata
            if self.detector.process_audio_chunk(mono_data):
                self.trigger_action()

        mode_desc = "SINGLE clap" if self.detector.single_clap else "DOUBLE clap"
        logger.info(f"Listening for {mode_desc} on default microphone (sensitivity threshold={self.detector.energy_threshold})...")
        logger.info("Clap hands to kick-start backend, boot Next.js web frontend, and launch browser. Press Ctrl+C to exit.")

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
