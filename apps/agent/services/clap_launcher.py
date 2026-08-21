"""
Clap Audio Trigger & Smart Auto-Launcher Service.

Listens to real-time host microphone input using `sounddevice` and `numpy`.
Detects sharp clap sounds (single clap or double clap) and automatically:
1. Kills stale orphan process instances on ports 8000 & 3000 to prevent port conflicts.
2. Boots FastAPI backend server (port 8000).
3. Boots Next.js web frontend dev server (port 3000).
4. Launches http://localhost:3000/ (Voice UI) and http://localhost:3000/dashboard (Admin Dashboard) without tab duplication.
"""

import time
import logging
import os
import sys
import subprocess
import webbrowser
import urllib.request
import threading
from typing import Optional, Callable, Set
import numpy as np

logger = logging.getLogger("agent.clap_launcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def kill_stale_port_processes(port: int):
    """
    Kills any stale/orphan background process listening on the specified TCP port.
    Prevents port conflicts and stale terminal processes.
    """
    try:
        if sys.platform == "win32":
            cmd = f"netstat -ano | findstr :{port}"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout:
                pids: Set[str] = set()
                for line in res.stdout.strip().split("\n"):
                    parts = line.strip().split()
                    if len(parts) >= 5 and "LISTENING" in line:
                        pids.add(parts[-1])
                for pid in pids:
                    if pid != "0" and int(pid) != os.getpid():
                        logger.info(f"Killing stale process on port {port} (PID: {pid})...")
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(f"fuser -k {port}/tcp", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.debug(f"Process cleanup notice for port {port}: {e}")


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
        refractory_period: float = 8.0,
    ):
        self.energy_threshold = energy_threshold
        self.single_clap = single_clap
        self.min_clap_interval = min_clap_interval
        self.max_clap_interval = max_clap_interval
        self.refractory_period = refractory_period

        self.last_clap_time: Optional[float] = None
        self.last_trigger_time: float = 0.0
        self.in_peak: bool = False

    def process_audio_chunk(self, audio_data: np.ndarray, timestamp: Optional[float] = None) -> bool:
        now = timestamp if timestamp is not None else time.time()

        if now - self.last_trigger_time < self.refractory_period:
            return False

        if audio_data.dtype != np.float32:
            if np.issubdtype(audio_data.dtype, np.integer):
                max_int = float(np.iinfo(audio_data.dtype).max)
                audio_data = audio_data.astype(np.float32) / max_int

        peak = float(np.max(np.abs(audio_data)))

        if peak >= self.energy_threshold:
            if not self.in_peak:
                self.in_peak = True
                return self._register_clap_peak(now)
        else:
            self.in_peak = False

        if not self.single_clap and self.last_clap_time and (now - self.last_clap_time > self.max_clap_interval):
            self.last_clap_time = None

        return False

    def _register_clap_peak(self, now: float) -> bool:
        if self.single_clap:
            logger.info("👏 Single clap sound detected! Instant activation triggered!")
            self.last_trigger_time = now
            return True

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


DoubleClapDetector = SingleOrDoubleClapDetector


class ClapLauncher:
    """
    Service wrapper around SingleOrDoubleClapDetector that manages system processes and browser tabs:
    - Kills orphan processes on ports 8000 and 3000.
    - Boots FastAPI backend server AND Next.js web frontend.
    - Opens http://localhost:3000/ and http://localhost:3000/dashboard without duplicate tab spam.
    """

    def __init__(
        self,
        backend_url: str = "http://localhost:8000/health",
        frontend_urls: Optional[list] = None,
        backend_cmd: Optional[str] = None,
        frontend_cmd: Optional[str] = None,
        detector: Optional[SingleOrDoubleClapDetector] = None,
    ):
        self.backend_url = backend_url
        self.frontend_urls = frontend_urls or [
            "http://localhost:3000/",
            "http://localhost:3000/dashboard",
            "http://localhost:8000",
        ]
        self.backend_cmd = backend_cmd
        self.frontend_cmd = frontend_cmd
        self.detector = detector or SingleOrDoubleClapDetector(single_clap=True, energy_threshold=0.18)
        self.last_browser_open_time: float = 0.0

    def is_backend_running(self) -> bool:
        try:
            req = urllib.request.Request(self.backend_url, headers={"User-Agent": "ClapLauncher"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def is_frontend_running(self) -> bool:
        try:
            req = urllib.request.Request(self.frontend_urls[0], headers={"User-Agent": "ClapLauncher"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status in (200, 304, 404)
        except Exception:
            return False

    def start_backend_async(self):
        if self.is_backend_running():
            logger.info("Backend service is already healthy and running (port 8000).")
            return

        logger.info("Starting FastAPI backend server process...")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Run from apps/agent so local imports (core, services, etc.) resolve correctly.
        # config.py uses an absolute path for .env so it still finds the root .env file.
        agent_dir = os.path.abspath(os.path.join(current_dir, ".."))

        cmd = self.backend_cmd or (
            f"{sys.executable} -m uvicorn main:app "
            f"--host 0.0.0.0 --port 8000"
        )

        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            subprocess.Popen(
                cmd,
                shell=True,
                cwd=agent_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            logger.info("Backend process spawned asynchronously.")
        except Exception as e:
            logger.error(f"Failed to spawn backend process: {e}")



    def start_frontend_async(self):
        if self.is_frontend_running():
            logger.info("Web frontend service is already running (port 3000).")
            return

        logger.info("Starting Next.js web application frontend server (npm run dev)...")
        cmd = self.frontend_cmd or "npm run dev"

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

    def focus_existing_browser_window(self) -> bool:
        """
        Scans top-level windows for open browser windows containing 'my_agent', 'dashboard',
        or 'localhost:3000' and brings the browser window to focus.
        Returns True if an existing browser window was found and focused (NO duplicate tabs opened).
        """
        if sys.platform != "win32":
            return False

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            focused = False

            def enum_callback(hwnd, lparam):
                nonlocal focused
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    
                    title_lower = title.lower()
                    if ("my_agent" in title_lower or "dashboard" in title_lower or "localhost:3000" in title_lower) and "antigravity" not in title_lower and "code" not in title_lower:
                        logger.info(f"Focused open browser window '{title}'. No duplicate tab opened!")
                        SW_RESTORE = 9
                        user32.ShowWindow(hwnd, SW_RESTORE)
                        user32.SetForegroundWindow(hwnd)
                        focused = True
                        return False
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            return focused
        except Exception as e:
            logger.debug(f"Window focus check error: {e}")
            return False

    def open_browser_tabs(self):
        """Opens the 3 app browser tabs. Skips if triggered within 30 seconds of last open."""
        now = time.time()
        if now - self.last_browser_open_time < 30.0:
            logger.info("Browser tabs were recently opened. Skipping duplicate launch.")
            return

        self.last_browser_open_time = now

        for idx, url in enumerate(self.frontend_urls):
            logger.info(f"Launching browser tab #{idx + 1}: {url}")
            try:
                webbrowser.open_new_tab(url)
            except Exception as e:
                logger.error(f"Failed to open browser tab for {url}: {e}")
            time.sleep(0.6)


    def trigger_action(self):
        """Executes non-blocking parallel kick-start sequence on clap detection."""
        logger.info("👏 CLAP ACTIVATION CONFIRMED: Checking servers and opening browser tabs!")
        
        # Check and spawn missing servers in parallel background threads
        t1 = threading.Thread(target=self.start_backend_async, daemon=True)
        t2 = threading.Thread(target=self.start_frontend_async, daemon=True)
        t3 = threading.Thread(target=self.open_browser_tabs, daemon=True)
        t1.start()
        t2.start()
        t3.start()

    def listen(self, sample_rate: int = 44100, block_size: int = 2048):
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("`sounddevice` package is required for real-time audio input.")
            logger.error("Please install dependencies: pip install sounddevice")
            sys.exit(1)

        try:
            from services.wake_word_service import wake_word_detector
        except ImportError:
            wake_word_detector = None

        def audio_callback(indata: np.ndarray, frames: int, time_info, status):
            if status:
                logger.warning(f"Audio status warning: {status}")
            
            mono_data = indata[:, 0] if indata.ndim > 1 else indata

            # 1. Check Clap Sound Trigger
            clap_triggered = self.detector.process_audio_chunk(mono_data)

            # 2. Check "Agent" Voice Command Trigger
            voice_triggered = False
            if wake_word_detector:
                v_trig, is_authed, speaker_name = wake_word_detector.process_audio_chunk(mono_data)
                voice_triggered = v_trig

            if clap_triggered:
                logger.info("👏 CLAP SOUND TRIGGER DETECTED!")
                self.trigger_action()
            elif voice_triggered:
                logger.info("🗣️ VOICE ACTIVATION COMMAND DETECTED ('Agent')!")
                self.trigger_action()

        mode_desc = "SINGLE clap" if self.detector.single_clap else "DOUBLE clap"
        if sys.platform == "win32":
            os.system("")

        GREEN_BOLD = "\033[1;92m"
        GREEN = "\033[92m"
        CYAN = "\033[96m"
        RESET = "\033[0m"

        print(f"\n{GREEN}============================================================{RESET}")
        print(f"{GREEN_BOLD}  [+] AGENT ACTIVE{RESET}")
        print(f"{GREEN}============================================================{RESET}")
        print(f"{CYAN}  Listening for hand claps ({mode_desc}) OR 'Agent' voice command...{RESET}\n")

        logger.info(f"Listening on default microphone for hand claps OR 'Agent' voice command...")

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
            logger.info("Stopped agent listener.")
        except Exception as e:
            logger.error(f"Microphone audio streaming error: {e}")


if __name__ == "__main__":
    launcher = ClapLauncher()
    launcher.listen()
