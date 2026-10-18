"""
Procedural Tools: Tools to load unbreakable business rules and fetch procedural skills.
"""
import os
import logging
from pathlib import Path
from typing import Optional
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func

logger = logging.getLogger("agent.tools.procedural")


def get_memory_dir() -> Path:
    """
    Locates and returns the memory/ directory path.
    """
    module_root = Path(__file__).resolve().parent.parent.parent.parent
    possible_dirs = [
        module_root / "memory",
        Path.cwd() / "memory",
        Path.cwd().parent / "memory",
        Path.cwd().parent.parent / "memory",
    ]
    for d in possible_dirs:
        if d.exists() and d.is_dir():
            return d

    default_dir = module_root / "memory"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def load_unbreakable_rules() -> str:
    """
    Reads memory/rules.md and returns the unbreakable constraints as a string.
    This string is injected as a high-priority system message in generation nodes.
    """
    mem_dir = get_memory_dir()
    rules_path = mem_dir / "rules.md"

    if not rules_path.exists():
        logger.warning(f"Rules file missing at {rules_path}. Creating default rules.md...")
        default_rules = (
            "# UNBREAKABLE BUSINESS RULES\n"
            "1. **DISCOUNT FLOOR:** Under no circumstances may any service or quote be discounted below 13.47%.\n"
            "2. **NO BLIND QUOTES:** Never provide an exact price without establishing a clear scope.\n"
            "3. **COMMUNICATION:** Always include contact email (pharezsigasa@gmail.com) and phone (+447544357979).\n"
        )
        try:
            with open(rules_path, "w", encoding="utf-8") as f:
                f.write(default_rules)
            return default_rules
        except Exception as e:
            logger.error(f"Error creating default rules.md: {e}")
            return "1. DISCOUNT FLOOR: Under no circumstances may any service or quote be discounted below 13.47%."

    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content if content else "1. DISCOUNT FLOOR: Under no circumstances may any service or quote be discounted below 13.47%."
    except Exception as e:
        logger.error(f"Error loading unbreakable rules: {e}")
        return "1. DISCOUNT FLOOR: Under no circumstances may any service or quote be discounted below 13.47%."


def fetch_skill(task_name: str) -> str:
    """
    Searches the memory/procedures/ directory for a markdown file matching the task_name intent.
    Returns the step-by-step procedure instructions.
    """
    mem_dir = get_memory_dir()
    proc_dir = mem_dir / "procedures"

    if not proc_dir.exists():
        proc_dir.mkdir(parents=True, exist_ok=True)
        return ""

    task_clean = task_name.lower().replace(" ", "_").replace("-", "_")

    possible_files = list(proc_dir.glob("*.md"))
    for file_path in possible_files:
        stem = file_path.stem.lower()
        if task_clean in stem or stem in task_clean:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    logger.info(f"Retrieved skill procedure from {file_path.name}")
                    return f"=== PROCEDURAL SKILL: {file_path.name} ===\n{content}"
            except Exception as e:
                logger.error(f"Error reading procedure file {file_path}: {e}")

    # Keyword match search
    keywords = [k for k in task_clean.split("_") if len(k) > 2]
    for file_path in possible_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if any(kw in content.lower() or kw in file_path.name.lower() for kw in keywords):
                    logger.info(f"Matched keyword skill procedure from {file_path.name}")
                    return f"=== PROCEDURAL SKILL: {file_path.name} ===\n{content}"
        except Exception:
            pass

    return ""


def list_available_skills() -> list[str]:
    """
    Scans memory/procedures/ and returns a list of all active learned SOP skill filenames.
    """
    mem_dir = get_memory_dir()
    proc_dir = mem_dir / "procedures"
    if not proc_dir.exists():
        return []
    return [f.name for f in proc_dir.glob("*.md")]
