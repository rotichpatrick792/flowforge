# ADR 0001: Phase 1 Foundation Choices

**Status:** Accepted
**Date:** 2026-10-01

## Context

FlowForge is a distributed workflow orchestration engine. Before any queue,
worker, or database code is written, the service foundation must support
observability, type safety, and configuration hygiene.

## Decisions

### 1. Structured logging (structlog) with correlation IDs
Plain `logging` produces unstructured strings. Structlog emits JSON with
typed fields, and every log line within an HTTP request carries a
`request_id` (honored from `X-Request-ID` if provided). This is the
foundation for tracing a single task across the API, queue, and worker in
later phases.

### 2. OpenTelemetry from day one
Traces are wired into the FastAPI app via `FastAPIInstrumentor`. In dev,
spans go to the console. In later phases the exporter swaps to OTLP with no
change to call sites.

### 3. Prometheus metrics on a dedicated registry
Using a custom `CollectorRegistry` (rather than the default) keeps our
metrics separate from Python process metrics and makes testing deterministic.

### 4. Liveness vs. readiness endpoints
`/healthz` is dependency-free. `/readyz` will grow dependency checks
(Postgres in Phase 2, Redis in Phase 3). The distinction matters for
container orchestrators.

### 5. Application factory + lifespan hooks
`create_app()` returns an isolated FastAPI instance, so tests can spin up
apps with overridden settings. Startup/shutdown logic lives in the
`lifespan` context manager.

### 6. Strict mypy and ruff from the start
Retrofitting strict typing onto an existing codebase is expensive. We
enforce it from the first file. Third-party packages with incompatible
syntax are excluded via `follow_imports = "skip"` overrides.

## Consequences

- All code must be typed; `Any` returns require explicit `cast()`.
- Every request automatically produces a structured log line and an OTel span.
- Adding a new dependency may require a mypy override if the package's
  stubs use newer syntax than the target Python version.