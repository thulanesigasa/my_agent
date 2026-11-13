"""
Self-Healing Python Code Execution Sandbox Service.

Executes Python data processing scripts in an isolated subprocess environment with strict timeouts.
If code execution encounters an exception or traceback, the self-healing engine automatically feeds the
error back to the LLM to patch the code and retry execution until clean output is achieved.
"""

import sys
import os
import tempfile
import subprocess
import logging
from typing import Dict, Any, Tuple
try:
    from services.llm_factory import get_drafting_llm
except ImportError:
    def get_drafting_llm():
        class MockLLM:
            async def ainvoke(self, messages):
                class MockRes:
                    content = "```python\n# Repaired code\nprint('Fixed')\n```"
                return MockRes()
        return MockLLM()

logger = logging.getLogger("agent.sandbox_service")


class PythonSandboxService:
    """
    Isolated Python Subprocess Execution Sandbox with Automated LLM Self-Healing Loop.
    """

    def __init__(self, default_timeout: float = 10.0):
        self.default_timeout = default_timeout

    def run_code_raw(self, code: str, timeout: float = 10.0) -> Tuple[bool, str, str]:
        """
        Executes raw Python code string in an isolated subprocess sandbox.
        Returns: (success: bool, stdout: str, stderr: str)
        """
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            cmd = [sys.executable, tmp_path]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()
            )
            success = proc.returncode == 0
            return success, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Execution timed out after {timeout} seconds."
        except Exception as e:
            return False, "", str(e)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    async def execute_with_self_healing(self, code: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Executes code snippet. If an exception occurs, automatically passes error traceback to LLM
        to repair the script and retries execution up to max_retries times.
        """
        current_code = code
        repair_logs = []

        for attempt in range(1, max_retries + 1):
            logger.info(f"Sandbox execution attempt #{attempt}/{max_retries}...")
            success, stdout, stderr = self.run_code_raw(current_code, timeout=self.default_timeout)

            if success and "Traceback (most recent call last):" not in stderr:
                logger.info(f"✅ Sandbox execution succeeded on attempt #{attempt}!")
                return {
                    "success": True,
                    "attempts": attempt,
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip(),
                    "final_code": current_code,
                    "repair_logs": repair_logs
                }

            # Code failed - record error and trigger self-healing
            error_message = stderr.strip() or "Process exited with non-zero status code."
            logger.warning(f"⚠️ Sandbox execution attempt #{attempt} failed with error:\n{error_message}")
            repair_logs.append({"attempt": attempt, "error": error_message, "failed_code": current_code})

            if attempt == max_retries:
                break

            # LLM Self-Healing Code Repair Prompt
            logger.info(f"🔄 Activating LLM Self-Healing code repair loop (Attempt {attempt} -> {attempt + 1})...")
            llm = get_drafting_llm()

            healing_prompt = (
                "You are an expert Python self-healing code repair engine.\n"
                "The following Python script failed during sandbox execution.\n\n"
                "=== FAILED CODE ===\n"
                f"{current_code}\n\n"
                "=== ERROR TRACEBACK ===\n"
                f"{error_message}\n\n"
                "Analyze the exact cause of the error (e.g. KeyError, TypeError, SyntaxError, Missing Import, Index Out of Bounds).\n"
                "Provide the complete, corrected Python code ready for execution.\n"
                "Output ONLY executable Python code within ```python ``` block."
            )

            try:
                res = await llm.ainvoke([
                    {"role": "system", "content": "You output only valid executable Python code in ```python``` blocks."},
                    {"role": "user", "content": healing_prompt}
                ])
                res_text = res.content if hasattr(res, "content") else str(res)

                # Extract python block
                start_marker = "```python"
                end_marker = "```"
                if start_marker in res_text:
                    code_start = res_text.find(start_marker) + len(start_marker)
                    code_end = res_text.find(end_marker, code_start)
                    repaired_code = res_text[code_start:code_end].strip()
                elif "```" in res_text:
                    code_start = res_text.find("```") + 3
                    code_end = res_text.find("```", code_start)
                    repaired_code = res_text[code_start:code_end].strip()
                else:
                    repaired_code = res_text.strip()

                current_code = repaired_code
            except Exception as patch_err:
                logger.error(f"Failed to generate self-healing patch: {patch_err}")

        return {
            "success": False,
            "attempts": max_retries,
            "stdout": "",
            "stderr": f"Failed after {max_retries} self-healing attempts. Last error: {stderr.strip()}",
            "final_code": current_code,
            "repair_logs": repair_logs
        }


sandbox_service = PythonSandboxService()
