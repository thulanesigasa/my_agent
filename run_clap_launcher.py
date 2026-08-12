#!/usr/bin/env python3
"""
Unified Clap & "Agent" Voice Command Listener Launcher Entrypoint.

Usage:
    python run_clap_launcher.py

Clap hands OR say "Agent" into your microphone to:
1. Boot/ensure the FastAPI agent backend is running (http://localhost:8000).
2. Boot/ensure the Next.js web frontend is running (http://localhost:3000).
3. Open or focus the application tabs in your browser.
"""

import os
import sys

# Add apps/agent to python path for modular import
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_path = os.path.join(current_dir, "apps", "agent")
if agent_path not in sys.path:
    sys.path.insert(0, agent_path)

try:
    from apps.agent.services.clap_launcher import ClapLauncher
except ImportError:
    from services.clap_launcher import ClapLauncher

if __name__ == "__main__":
    launcher = ClapLauncher()
    launcher.listen()
