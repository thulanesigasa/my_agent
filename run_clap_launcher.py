#!/usr/bin/env python3
"""
Double-Clap Trigger Launcher Entrypoint.

Usage:
    python run_clap_launcher.py

Clap hands TWICE in quick succession (within 150ms to 750ms) to:
1. Boot/ensure the FastAPI agent backend is running (http://localhost:8000).
2. Automatically launch the web application in your browser (http://localhost:3000).
"""

import os
import sys

# Add apps/agent to python path for modular import
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_path = os.path.join(current_dir, "apps", "agent")
if agent_path not in sys.path:
    sys.path.insert(0, agent_path)

from services.clap_launcher import ClapLauncher

if __name__ == "__main__":
    launcher = ClapLauncher()
    launcher.listen()
