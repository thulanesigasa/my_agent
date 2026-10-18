"""Health reports distinguish local checks from provider configuration."""

from fastapi import APIRouter
from config import settings
from core.store import store
from core.memory import memory_manager
from services.email_service import email_service

router = APIRouter(tags=["Health"])


@router.get("/health/detailed")
async def detailed_system_health():
    services = {}
    try:
        with store.connect() as db:
            db.execute("SELECT 1").fetchone()
        services["workflow_store"] = {
            "status": "UP",
            "latency_ms": 0,
            "details": "Local database readable",
        }
    except Exception:
        services["workflow_store"] = {
            "status": "DOWN",
            "latency_ms": 0,
            "details": "Local database unavailable",
        }
    services["memory"] = {
        "status": "CONFIGURED" if memory_manager.client else "LOCAL",
        "latency_ms": 0,
        "details": "Provider connectivity is not verified by this check",
    }
    services["gmail"] = {
        "status": "CONFIGURED" if email_service.client else "NOT_CONFIGURED",
        "latency_ms": 0,
    }
    services["llm"] = {
        "status": (
            "CONFIGURED"
            if any(
                (
                    settings.GROQ_API_KEY,
                    settings.GEMINI_API_KEY,
                    settings.OPENROUTER_API_KEY,
                )
            )
            else "NOT_CONFIGURED"
        ),
        "latency_ms": 0,
    }
    ready = (
        services["workflow_store"]["status"] == "UP"
        and services["gmail"]["status"] == "CONFIGURED"
        and services["llm"]["status"] == "CONFIGURED"
    )
    return {
        "status": "UP" if ready else "DEGRADED",
        "environment": settings.ENV,
        "services": services,
    }
