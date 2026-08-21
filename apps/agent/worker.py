"""
Continuous Background Task Worker & Event Scheduler.
Periodically polls Gmail unread messages every 60 seconds and feeds them into the LangGraph State Machine.
"""
import asyncio
import logging
from typing import Dict, Any

from core.state import AgentState
from core.graph import agent_workflow
from services.email_service import email_service
from services.whatsapp_service import whatsapp_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent.worker")


async def poll_unread_emails_job():
    """
    Periodically fetches unread emails and feeds them to the LangGraph execution engine.
    """
    logger.info("Worker polling unread emails from Gmail...")
    try:
        emails = await email_service.fetch_unread_emails(max_results=5)
        for email_item in emails:
            thread_id = email_item.get("thread_id", "email_job_thread")
            logger.info(f"Worker processing email from {email_item.get('sender')}: '{email_item.get('subject')}'")

            config = {"configurable": {"thread_id": thread_id}}
            initial_state: AgentState = {
                "messages": [{"role": "user", "content": f"Subject: {email_item.get('subject')}\nBody: {email_item.get('body')}"}],
                "email_input": email_item,
                "approval_status": "none"
            }

            final_state = await agent_workflow.ainvoke(initial_state, config=config)
            logger.info(f"Processed email thread '{thread_id}'. Intent: {final_state.get('intent')}, Approval Required: {final_state.get('needs_human_approval')}")
    except Exception as e:
        logger.error(f"Error in poll_unread_emails_job: {e}", exc_info=True)


async def main():
    """
    Worker 24/7 main async polling loop.
    """
    logger.info("Starting Autonomous Agent Background Worker Process...")
    POLL_INTERVAL_SECONDS = 60

    while True:
        try:
            await poll_unread_emails_job()
        except Exception as err:
            logger.critical(f"Unhandled worker Exception caught: {err}. Recovering loop in 10s...")
            await asyncio.sleep(10)
        
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
