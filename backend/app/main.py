"""FlowForge API entrypoint."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api import health, tasks
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.telemetry import configure_telemetry
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown hooks."""
    log = get_logger(__name__)
    settings = get_settings()
    log.info(
        "app_startup",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )
    try:
        yield
    finally:
        await dispose_engine()
        log.info("app_shutdown")

def create_app() -> FastAPI:
    """Application factory.

    Using a factory (instead of a module-level `app = FastAPI()`) lets tests
    construct isolated app instances with overridden settings.
    """
    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        json_output=settings.app_env != "dev",
    )
    configure_telemetry(
        service_name=settings.otel_service_name,
        service_version=settings.app_version,
        environment=settings.app_env,
        exporter=settings.otel_exporter,
        enabled=settings.otel_enabled,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Middleware order matters: outermost first.
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health.router)
    app.include_router(tasks.router)

    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()
