"""
Sandbox Tools: Allows LangGraph agent nodes to safely execute Python scripts and data analysis
with automated LLM self-healing error recovery.
"""

import asyncio
import logging
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func
from services.sandbox_service import sandbox_service

logger = logging.getLogger("agent.tools.sandbox")


@tool
async def run_self_healing_python_analysis(code: str) -> str:
    """
    Executes Python data analysis code inside an isolated self-healing sandbox environment.
    If the script fails due to a bug or exception, the self-healing engine automatically repairs the code
    and retries execution up to 3 times before returning the final result.

    :param code: Python script code to execute.
    :return: Formatted string containing stdout execution result or error traceback.
    """
    logger.info("Executing Python code in Self-Healing Sandbox tool...")
    res = await sandbox_service.execute_with_self_healing(code=code, max_retries=3)

    if res["success"]:
        attempts_str = f" (Succeeded after {res['attempts']} attempt{'s' if res['attempts'] > 1 else ''})"
        return f"=== SANDBOX EXECUTION OUTPUT{attempts_str} ===\n{res['stdout']}"
    else:
        return f"=== SANDBOX EXECUTION FAILED ({res['attempts']} attempts) ===\n{res['stderr']}"
