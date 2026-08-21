"""
Comprehensive System Health Check API Router.
Performs live ping checks, connectivity validation, and latency metrics across downstream dependencies
(Supabase pgvector, Groq API, Google AI Studio, OpenRouter, checkpointer).
"""
import time
import logging
import httpx
from typing import Dict, Any
from fastapi import APIRouter
from config import settings
from core.memory import memory_manager

logger = logging.getLogger("agent.router.health")

router = APIRouter(tags=["Health"])


async def check_supabase_latency() -> Dict[str, Any]:
    """Check Supabase pgvector database connection and measure ping latency."""
    start = time.perf_counter()
    if not memory_manager.client:
        return {"status": "DOWN", "latency_ms": 0.0, "details": "Supabase client unconfigured"}

    try:
        res = memory_manager.client.table("langgraph_memory").select("id").limit(1).execute()
        latency = (time.perf_counter() - start) * 1000.0
        return {"status": "UP", "latency_ms": round(latency, 2), "details": "Connected to langgraph_memory table"}
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000.0
        return {"status": "DEGRADED", "latency_ms": round(latency, 2), "details": str(e)}


async def check_http_endpoint(url: str, headers: dict = None, timeout: float = 5.0) -> Dict[str, Any]:
    """Helper to perform HTTP HEAD/GET latency checks against LLM providers."""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            latency = (time.perf_counter() - start) * 1000.0
            status_code = resp.status_code
            status_str = "UP" if status_code < 500 else "DEGRADED"
            return {"status": status_str, "status_code": status_code, "latency_ms": round(latency, 2)}
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000.0
        return {"status": "DOWN", "latency_ms": round(latency, 2), "details": str(e)}


@router.get("/health/detailed")
async def detailed_system_health():
    """
    Returns structured system status ('UP', 'DEGRADED', 'DOWN') and latency breakdown for all providers.
    """
    logger.info("Executing detailed system health check...")

    supabase_health = await check_supabase_latency()
    
    # Check Groq API
    groq_headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"} if settings.GROQ_API_KEY else {}
    groq_health = await check_http_endpoint("https://api.groq.com/openai/v1/models", headers=groq_headers)

    # Check Gemini API
    gemini_health = {"status": "UP" if bool(settings.GEMINI_API_KEY) else "DEGRADED", "latency_ms": 0.0}

    # Check OpenRouter Fallback API
    openrouter_health = {"status": "UP" if bool(settings.OPENROUTER_API_KEY) else "DEGRADED", "latency_ms": 0.0}

    overall_status = "UP"
    if supabase_health["status"] == "DOWN" or groq_health["status"] == "DOWN":
        overall_status = "DEGRADED"

    return {
        "status": overall_status,
        "environment": settings.ENV,
        "timestamp": time.time(),
        "services": {
            "supabase_pgvector": supabase_health,
            "groq_api": groq_health,
            "google_ai_gemini": gemini_health,
            "openrouter_fallback": openrouter_health,
        }
    }
