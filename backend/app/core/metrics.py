"""Prometheus metrics registry and helpers."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)
from starlette.responses import Response

# A dedicated registry keeps our metrics separate from the default process
# collector noise and makes testing deterministic.
REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS_TOTAL = Counter(
    "flowforge_http_requests_total",
    "Total HTTP requests handled by the API.",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Gauge(
    "flowforge_http_request_duration_seconds_last",
    "Duration of the most recent request in seconds (label: path).",
    labelnames=("path",),
    registry=REGISTRY,
)


def metrics_response() -> Response:
    """Return the Prometheus text exposition as a Starlette Response."""
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
