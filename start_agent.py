#!/usr/bin/env python3
"""
Custom 'start agent' CLI Terminal Entrypoint.

Usage in Terminal:
    start agent
  OR
    python start_agent.py

Displays vibrant green 'AGENT ACTIVE' status banner and starts real-time microphone
listening for EITHER hand claps OR the 'Agent' voice command trigger.
"""

import os
import sys

# Enable ANSI escape color codes in Windows Command Prompt and PowerShell
if sys.platform == "win32":
    os.system("")

GREEN_BOLD = "\033[1;92m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"

# Add apps/agent to Python path for modular import
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_path = os.path.join(current_dir, "apps", "agent")
if agent_path not in sys.path:
    sys.path.insert(0, agent_path)

try:
    from apps.agent.services.clap_launcher import ClapLauncher
except ImportError:
    from services.clap_launcher import ClapLauncher


def print_active_banner():
    banner = f"""
{GREEN}============================================================{RESET}
{GREEN_BOLD}  [+] AGENT ACTIVE{RESET}
{GREEN}============================================================{RESET}
{CYAN}  Listening for hand claps OR 'Agent' voice command...{RESET}
  Press Ctrl+C to stop the listener.
"""
    print(banner)


if __name__ == "__main__":
    print_active_banner()
    launcher = ClapLauncher()
    launcher.listen()
