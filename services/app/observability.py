"""OpenTelemetry tracing: one VAR event fanned out across the pipeline as spans.

A TracerProvider with a ConsoleSpanExporter is installed once when the FastAPI app
starts, so a running server prints each request's span tree (the HTTP request span
from the FastAPI instrumentation, with the pipeline stages -- geometry, law, granite,
guardian -- nested underneath) to stdout. No OpenTelemetry Collector is required.

The pipeline imports ``tracer`` from here and wraps each stage in a span. The
OpenTelemetry API tracer is a no-op until a provider is installed, so importing it in
the tests (which never call ``setup_tracing``) costs nothing and prints nothing.
"""

from __future__ import annotations

from opentelemetry import trace

SERVICE_NAME = "varsity-backend"

# No-op until setup_tracing() installs an SDK provider.
tracer = trace.get_tracer("varsity.pipeline")

_configured = False


def setup_tracing(app: object) -> None:
    """Install a console-exporting TracerProvider and instrument the FastAPI app."""
    global _configured
    if _configured:
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME as RES_SERVICE_NAME
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider(resource=Resource.create({RES_SERVICE_NAME: SERVICE_NAME}))
    # SimpleSpanProcessor flushes each span to the console the moment it ends.
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    _configured = True
