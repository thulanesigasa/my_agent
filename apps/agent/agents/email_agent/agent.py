"""Email agent entry point. Sending requires an explicit persisted approval."""


async def run_email_agent(query="Send emails", recipients=None):
    return {
        "agent": "email_agent",
        "status": "requires_approval",
        "query": query,
        "emails_sent_count": 0,
        "message": "Review a saved draft in the Approval Queue before sending.",
    }
