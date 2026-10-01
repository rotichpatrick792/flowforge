"""Health, readiness, and metrics endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.metrics import metrics_response

router = APIRouter(tags=["ops"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    """Liveness: process is up and event loop is responsive.

    Intentionally dependency-free. If this fails, the process is broken.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/readyz", summary="Readiness probe")
async def readyz() -> JSONResponse:
    """Readiness: dependencies required to serve traffic are reachable.

    In Phase 1 we have no dependencies, so this mirrors liveness.
    Phase 2 will add Postgres, Phase 3 will add Redis.
    """
    checks: dict[str, str] = {"config": "ok"}
    ready = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "checks": checks,
        },
    )


@router.get("/metrics", summary="Prometheus metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus text exposition endpoint."""
    return metrics_response()
