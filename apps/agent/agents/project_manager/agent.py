"""Expose recorded task states rather than claiming all agents are healthy."""

from core.store import store


async def run_project_manager(query="Audit agent activity"):
    tasks = store.list("tasks")
    return {
        "agent": "project_manager",
        "status": "completed",
        "query": query,
        "tasks": tasks,
        "failed_tasks": sum(t["status"] == "failed" for t in tasks),
        "held_approvals": [
            a
            for a in store.list("approvals")
            if a["status"] in ("sending", "delivery_unknown", "failed")
        ],
    }
