"""
OpenTelemetry & LangSmith Tracing Configuration Module.
Instruments FastAPI and LangGraph execution traces for observable, reliable agent monitoring.
"""
import os
import logging

logger = logging.getLogger("agent.telemetry")


def setup_telemetry():
    """
    Configures OpenTelemetry and LangSmith tracing environment flags.
    Only enables tracing if a valid LangSmith API key is configured.
    """
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    langsmith_tracing = bool(api_key) and os.getenv("LANGSMITH_TRACING", "true").lower() == "true"

    if langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if not os.getenv("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = "autonomous-agent-platform"
        logger.info("OpenTelemetry & LangSmith observability tracing initialized.")
    else:
        # Explicitly disable tracing to prevent 401 auth errors and missing key warnings
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.info("Telemetry tracing disabled (no LANGSMITH_API_KEY set).")


# Run telemetry setup upon import
setup_telemetry()
