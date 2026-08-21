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
    Routes traces to LangSmith OTLP endpoint if configured.
    """
    langsmith_tracing = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
    langsmith_otel = os.getenv("LANGSMITH_OTEL_ENABLED", "true").lower() == "true"

    if langsmith_tracing or langsmith_otel:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if not os.getenv("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = "autonomous-agent-platform"

        logger.info("OpenTelemetry & LangSmith observability tracing initialized.")

        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

            provider = TracerProvider()
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            logger.info("OpenTelemetry TracerProvider configured.")
        except Exception as e:
            logger.debug(f"OpenTelemetry SDK setup notice: {e}")
    else:
        logger.info("Telemetry tracing disabled.")


# Run telemetry setup upon import
setup_telemetry()
