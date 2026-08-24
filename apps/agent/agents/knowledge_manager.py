"""
Knowledge Manager Node: Reflects on conversation state and autonomously updates knowledge/*.md files.
"""
import json
import logging
from core.state import AgentState
from services.llm_factory import get_drafting_llm
from tools.knowledge_tools import update_knowledge_file, read_company_knowledge

logger = logging.getLogger("agent.node.knowledge_manager")

KNOWLEDGE_UPDATER_PROMPT = """
You are the Knowledge Manager Node for T.s Industries.
Your role is to analyze inputs where an admin/user provides new business information, corrections, pricing rules, new service capabilities, or brand directives.

Analyze the message and determine which knowledge file should be updated:
- "about_us.md": Company identity, contacts, leadership, mission, core directives.
- "services_and_stack.md": Web development, mobile app dev, tech stack, new service offerings.
- "brand_voice.md": Communication tone, rules, constraints.
- "learned_insights.md": Specific business rules, learned facts, or insights that do not fit the above.

Respond strictly with a JSON object:
{
    "target_file": "about_us.md|services_and_stack.md|brand_voice.md|learned_insights.md",
    "content_to_write": "<clear concise Markdown text to add or update>",
    "append": true|false,
    "summary": "<summary of updated knowledge>"
}
"""

async def knowledge_updater_node(state: AgentState) -> AgentState:
    """
    Knowledge Updater Node: Autonomously updates knowledge files on disk.
    """
    logger.info("Executing Knowledge Updater Node...")
    messages = state.get("messages", [])

    last_msg = ""
    if messages:
        m = messages[-1]
        last_msg = m.get("content", "") if isinstance(m, dict) else str(getattr(m, "content", m))

    current_knowledge = read_company_knowledge()

    prompt = f"""
Current Knowledge Base Context:
{current_knowledge}

User/Admin Teaching Message:
{last_msg}

Analyze what new knowledge, rule, or capability was stated and format the update JSON.
"""

    llm = get_drafting_llm()
    try:
        res = await llm.ainvoke([
            {"role": "system", "content": KNOWLEDGE_UPDATER_PROMPT},
            {"role": "user", "content": prompt}
        ])
        output_str = res.content if hasattr(res, "content") else str(res)

        target_file = "learned_insights.md"
        content_to_write = ""
        append = True
        summary = "Updated company knowledge base."

        start_idx = output_str.find("{")
        end_idx = output_str.rfind("}")
        if start_idx != -1 and end_idx != -1:
            data = json.loads(output_str[start_idx:end_idx + 1])
            target_file = data.get("target_file", "learned_insights.md")
            content_to_write = data.get("content_to_write", "")
            append = data.get("append", True)
            summary = data.get("summary", summary)

        if content_to_write:
            tool_result = await update_knowledge_file.ainvoke({
                "file_name": target_file,
                "new_content": content_to_write,
                "append": append
            })
            result_text = f"[SUCCESS] Knowledge base updated: {summary} ({tool_result})"
        else:
            result_text = "[INFO] No explicit knowledge modification extracted from message."

    except Exception as e:
        logger.error(f"Error in knowledge_updater_node: {e}")
        result_text = f"[ERROR] Failed to update knowledge base: {e}"

    return {
        **state,
        "sender": "knowledge_manager",
        "final_output": result_text,
        "draft_response": result_text,
        "needs_human_approval": False
    }
