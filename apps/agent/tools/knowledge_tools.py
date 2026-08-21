"""
Dynamic Knowledge Tools: Runtime reading and autonomous writing to knowledge/*.md files.
"""
import os
import logging
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger("agent.tools.knowledge")


def get_knowledge_dir() -> Path:
    """
    Locates and returns the absolute knowledge/ directory path.
    """
    module_root = Path(__file__).resolve().parent.parent.parent.parent
    possible_dirs = [
        module_root / "knowledge",
        Path.cwd() / "knowledge",
        Path.cwd().parent / "knowledge",
        Path.cwd().parent.parent / "knowledge",
    ]
    for d in possible_dirs:
        if d.exists() and d.is_dir():
            return d

    # Default fallback creation
    default_dir = module_root / "knowledge"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def read_company_knowledge() -> str:
    """
    Opens the knowledge/ directory at runtime.
    Reads all .md files (about_us.md, services_and_stack.md, brand_voice.md, learned_insights.md).
    Returns a concatenated string of the current, up-to-the-second company context.
    """
    k_dir = get_knowledge_dir()
    context_parts = []

    if k_dir.exists():
        md_files = sorted(list(k_dir.glob("*.md")))
        for md_path in md_files:
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        context_parts.append(f"=== KNOWLEDGE FILE: {md_path.name} ===\n{content}")
            except Exception as e:
                logger.error(f"Error reading knowledge file {md_path}: {e}")

    result = "\n\n".join(context_parts)
    return result if result else "No company knowledge context found."


@tool
async def update_knowledge_file(file_name: str, new_content: str, append: bool = True) -> str:
    """
    Modifies or updates a markdown knowledge file in the knowledge/ directory.
    - file_name: Target filename (e.g., 'about_us.md', 'services_and_stack.md', 'brand_voice.md', 'learned_insights.md').
    - new_content: Content or fact to add or overwrite.
    - append: If True, appends to bottom of file; if False, overwrites file.
    """
    try:
        k_dir = get_knowledge_dir()

        # Security check: sanitize filename to prevent path traversal
        clean_filename = Path(file_name).name
        if not clean_filename.endswith(".md"):
            clean_filename = f"{clean_filename}.md"

        target_path = k_dir / clean_filename

        mode = "a" if append else "w"
        prefix = "\n\n" if append and target_path.exists() and target_path.stat().st_size > 0 else ""

        with open(target_path, mode, encoding="utf-8") as f:
            f.write(prefix + new_content.strip() + "\n")

        action = "appended to" if append else "updated"
        logger.info(f"Successfully {action} knowledge file: {target_path.name}")
        return f"Successfully {action} {target_path.name}."
    except Exception as e:
        logger.error(f"Error updating knowledge file {file_name}: {e}")
        return f"Error updating knowledge file {file_name}: {e}"
