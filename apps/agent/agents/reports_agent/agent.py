"""Return recorded activity only; weekly exports are implemented in Phase 3."""

from core.store import store


async def run_reports_agent(query="Generate weekly report"):
    return {
        "agent": "reports_agent",
        "status": "partial",
        "query": query,
        "metrics": store.metrics(),
        "limitations": ["Reply tracking and weekly exports are not available yet"],
    }
