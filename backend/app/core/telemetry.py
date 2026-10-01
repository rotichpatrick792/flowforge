"""OpenTelemetry initialization.

For now we export spans to the console so you can see traces locally.
Later phases will swap the exporter for OTLP -> Jaeger or Tempo without
changing any call sites.
"""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)


def _build_exporter(kind: str) -> SpanExporter | None:
    if kind == "console":
        return ConsoleSpanExporter()
    if kind == "none":
        return None
    raise ValueError(f"Unknown OTel exporter: {kind!r}")


def configure_telemetry(
    *,
    service_name: str,
    service_version: str,
    environment: str,
    exporter: str,
    enabled: bool = True,
) -> None:
    """Configure the global TracerProvider.

    Safe to call once per process. Calling twice would double-register
    exporters, so we guard on the current provider type.
    """
    if not enabled:
        return

    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )

    provider = TracerProvider(resource=resource)

    span_exporter = _build_exporter(exporter)
    if span_exporter is not None:
        if exporter == "console":
            provider.add_span_processor(SimpleSpanProcessor(span_exporter))
        else:
            provider.add_span_processor(BatchSpanProcessor(span_exporter))

    trace.set_tracer_provider(provider)
