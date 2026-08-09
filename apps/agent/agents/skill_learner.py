"""
Skill Learner Node: Formats user-taught procedures into structured SOPs and appends unbreakable rules.
"""
import json
import logging
from pathlib import Path
from core.state import AgentState
from services.llm_factory import get_drafting_llm
from tools.procedural_tools import get_memory_dir

logger = logging.getLogger("agent.node.skill_learner")

SKILL_LEARNER_PROMPT = """
You are the Skill Learner Node for T.S Industries.
Your role is to analyze user/admin messages where a new step-by-step procedure/skill or strict business rule is taught.

Determine the type of input:
1. "rule": A strict business constraint or rule that must never be broken (e.g., pricing limits, communication policies).
2. "procedure": A step-by-step Standard Operating Procedure (SOP) or skill (e.g. client onboarding, quote generation).

Respond strictly with a JSON object:
{
    "type": "rule|procedure",
    "filename": "<descriptive_name.md (e.g. client_onboarding.md)>",
    "content": "<structured Markdown content with numbered steps or rule statement>",
    "summary": "<short summary of learned skill or rule>"
}
"""

async def skill_learner_node(state: AgentState) -> AgentState:
    """
    Skill Learner Node: Formats instructions into SOPs or rule additions and writes to disk.
    """
    logger.info("Executing Skill Learner Node...")
    messages = state.get("messages", [])

    last_msg = ""
    if messages:
        m = messages[-1]
        last_msg = m.get("content", "") if isinstance(m, dict) else str(getattr(m, "content", m))

    llm = get_drafting_llm()
    result_text = ""

    try:
        res = await llm.ainvoke([
            {"role": "system", "content": SKILL_LEARNER_PROMPT},
            {"role": "user", "content": last_msg}
        ])
        output_str = res.content if hasattr(res, "content") else str(res)

        item_type = "procedure"
        filename = "learned_procedure.md"
        content = ""
        summary = "Learned new procedural skill."

        start_idx = output_str.find("{")
        end_idx = output_str.rfind("}")
        if start_idx != -1 and end_idx != -1:
            data = json.loads(output_str[start_idx:end_idx + 1])
            item_type = data.get("type", "procedure")
            filename = data.get("filename", filename)
            content = data.get("content", "")
            summary = data.get("summary", summary)

        mem_dir = get_memory_dir()

        if item_type == "rule":
            rules_path = mem_dir / "rules.md"
            with open(rules_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{content.strip()}\n")
            result_text = f"✅ New unbreakable rule saved to memory/rules.md: {summary}"
        else:
            proc_dir = mem_dir / "procedures"
            proc_dir.mkdir(parents=True, exist_ok=True)
            clean_fn = Path(filename).name
            if not clean_fn.endswith(".md"):
                clean_fn = f"{clean_fn}.md"
            target_path = proc_dir / clean_fn
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(f"# PROCEDURE: {clean_fn.replace('.md', '').replace('_', ' ').title()}\n\n{content.strip()}\n")
            result_text = f"✅ New procedural skill saved to memory/procedures/{clean_fn}: {summary}"

    except Exception as e:
        logger.error(f"Error in skill_learner_node: {e}")
        result_text = f"❌ Failed to process skill learning: {e}"

    return {
        **state,
        "sender": "skill_learner",
        "final_output": result_text,
        "draft_response": result_text,
        "needs_human_approval": False
    }
