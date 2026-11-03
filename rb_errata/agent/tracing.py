"""OpenTelemetry spans for the agent, viewed in a local Arize Phoenix (slice 14).

Off unless RB_TRACE_ENDPOINT is set (`make phoenix-up` serves one at
http://localhost:6006/v1/traces), so tests and ordinary runs export nothing
and need no server. Attribute names follow OpenInference, which Phoenix
reads to label spans as chains, retrievers and LLM calls.

Spans carry rule references and the (quote-guarded) answer, never passage
text: the trace store is local, but nothing in it should need to be.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace
from opentelemetry.trace import Span, Tracer

_configured = False
KIND = OpenInferenceSpanKindValues


def tracer() -> Tracer:
    """The agent's tracer; exports to Phoenix once, on first use, if configured."""
    global _configured
    endpoint = os.environ.get("RB_TRACE_ENDPOINT")
    if endpoint and not _configured:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": "rb-errata-agent"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        _configured = True
    return trace.get_tracer("rb_errata.agent")


@contextmanager
def span(name: str, kind: OpenInferenceSpanKindValues, **attrs: Any) -> Iterator[Span]:
    with tracer().start_as_current_span(name) as s:
        s.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, kind.value)
        for key, value in attrs.items():
            if value is not None:
                s.set_attribute(key, value)
        yield s


def flush() -> None:
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
