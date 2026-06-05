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
# An in-memory exporter so GET /trace can return the REAL span tree to a judge's browser, not just
# stdout. Holds the most-recent finished spans; cleared at the start of each /trace run.
_in_memory_spans: object | None = None


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
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    provider = TracerProvider(resource=Resource.create({RES_SERVICE_NAME: SERVICE_NAME}))
    # SimpleSpanProcessor flushes each span to the console the moment it ends.
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    # AND keep the last spans in memory so GET /trace can show the real span tree live in a browser.
    global _in_memory_spans
    _in_memory_spans = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(_in_memory_spans))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    _configured = True


def clear_captured_spans() -> None:
    """Reset the in-memory exporter before a traced run (so /trace returns that run's spans)."""
    if _in_memory_spans is not None:
        _in_memory_spans.clear()


def captured_span_tree() -> list[dict]:
    """The finished spans as {name, duration_ms, parent}, for the /trace judge receipt."""
    if _in_memory_spans is None:
        return []
    spans = _in_memory_spans.get_finished_spans()
    name_by_id = {s.context.span_id: s.name for s in spans}
    return [
        {
            "name": s.name,
            "duration_ms": round((s.end_time - s.start_time) / 1e6, 1),
            "parent": name_by_id.get(s.parent.span_id) if s.parent else None,
        }
        for s in spans
    ]
