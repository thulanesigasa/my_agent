"""
Drafter Agent Node: Synthesizes responses using Gemini 1.5 Pro, T.s Industries knowledge base,
unbreakable business rules, live CRM/Dashboard metrics, and procedural skills.
"""
import logging
from core.state import AgentState
from services.llm_factory import llm_factory
from core.memory import memory_manager
from tools.knowledge_tools import read_company_knowledge
from tools.procedural_tools import load_unbreakable_rules, fetch_skill
from agents.human_approval import get_pending_approvals
from services.crm_service import get_all_clients, get_all_projects
from tools.admin_tools import get_sent_emails

logger = logging.getLogger("agent.node.drafter")

DRAFTER_SYSTEM_PROMPT = """
You are the official representative of T.s Industries, a high-performance software engineering firm specializing in Web Development, Mobile Apps, and AI/Backend Integrations.

Follow these core directives strictly:
1. Speak as a representative of T.s Industries. Never say "I am an AI."
2. Always drive traffic to the website ts-industries.co.za for more details, portfolio showcases, or case studies.
3. Never quote exact pricing without established scope. Encourage booking a discovery call.
4. Maintain a professional yet approachable tone.
5. Use short, punchy paragraphs and bullet points. Never use em dashes (—).
6. When asked about clients, emails sent, pending approvals, or dashboard status, ALWAYS answer directly using the provided LIVE REAL-TIME DASHBOARD DATA. Never ask the user for clarification or timeframes when live data is provided below.
"""

async def drafter_node(state: AgentState) -> AgentState:
    """
    Drafter Node function for deep reasoning, skill execution, and response drafting.
    Dynamically loads knowledge/*.md, unbreakable rules, live CRM metrics, and procedural skills at runtime.
    """
    logger.info("Executing Drafter Node for T.s Industries...")
    messages = state.get("messages", [])
    intent = state.get("intent", "general")
    email_input = state.get("email_input")
    context = state.get("retrieved_context", [])

    # Read company knowledge dynamically at runtime
    company_knowledge = read_company_knowledge()

    # Load unbreakable rules and procedural skills
    unbreakable_rules = load_unbreakable_rules()

    user_input = ""
    if email_input and isinstance(email_input, dict):
        user_input = f"Subject: {email_input.get('subject', '')}\nBody: {email_input.get('body', '')}"
    elif messages:
        last_msg = messages[-1]
        user_input = last_msg.get("content", "") if isinstance(last_msg, dict) else str(getattr(last_msg, "content", last_msg))

    text_lower = user_input.lower()

    # Live Dashboard & CRM Data Query
    live_dashboard_lines = []
    if any(k in text_lower for k in ("client", "email", "approval", "dashboard", "report", "outreach", "status", "respond", "response")):
        # 1. Pending Approvals
        pending = get_pending_approvals()
        live_dashboard_lines.append(f"• Pending Email Approvals Queue: {len(pending)} item(s) awaiting approval.")
        for p in pending:
            live_dashboard_lines.append(f"   - Thread: {p.get('thread_id')} | Client: {p.get('client_name', 'Lead')} | Intent: {p.get('intent')}")

        # 2. CRM Clients
        try:
            clients = await get_all_clients()
            if clients:
                live_dashboard_lines.append(f"• CRM Registered Clients: {len(clients)} client(s) total.")
                for c in clients[:15]:
                    name = c.get("name") or c.get("client_name") or "Lead"
                    email = c.get("email") or c.get("client_email") or "N/A"
                    status = c.get("status") or "Active"
                    live_dashboard_lines.append(f"   - {name} ({email}) | Status: {status}")
            else:
                live_dashboard_lines.append("• CRM Registered Clients: 0 clients currently recorded in CRM database.")
        except Exception as e:
            logger.warning(f"CRM query warning: {e}")

        # 3. Sent Email Outbox Logs
        try:
            sent_info = await get_sent_emails(limit=10)
            live_dashboard_lines.append(f"• Email Outbox Log:\n{sent_info}")
        except Exception as e:
            logger.warning(f"Email log query warning: {e}")

    live_dashboard_context = "\n".join(live_dashboard_lines) if live_dashboard_lines else "No specific dashboard query requested."

    # Fetch matching procedural skill if applicable (e.g. quote, onboarding)
    task_keyword = "quote" if "quote" in text_lower or "pricing" in text_lower else intent
    skill_procedure = fetch_skill(task_keyword)

    # Additional query if context empty
    if not context:
        context = await memory_manager.search_memory(user_input, limit=3)

    context_str = "\n".join([f"- {c['content']}" for c in context]) if context else "No prior memory context."

    combined_system = f"""
{company_knowledge}

CRITICAL CONSTRAINTS:
{unbreakable_rules}

{DRAFTER_SYSTEM_PROMPT}
""".strip()

    prompt = f"""
Current Intent: {intent}
User Request:
{user_input}

LIVE REAL-TIME DASHBOARD DATA:
{live_dashboard_context}

{skill_procedure}

Retrieved Memory Context:
{context_str}

Please generate a detailed, polished response or draft message representing T.s Industries using the live real-time dashboard data above if requested. Follow all procedures and critical constraints.
"""

    draft_output = await llm_factory.invoke_drafter(prompt, combined_system)

    return {
        **state,
        "sender": "drafter",
        "draft_response": draft_output,
        "final_output": draft_output
    }
