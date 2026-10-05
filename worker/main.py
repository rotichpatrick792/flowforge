"""FlowForge worker process.

Reads task messages from the Redis Stream `flowforge:tasks` via the
consumer group `flowforge:workers`, executes the corresponding handler
from the whitelist, and updates the task record in Postgres.

Run with: `python -m worker`
"""

import asyncio
import json
import signal
import sys
from contextlib import suppress
from typing import Any
from uuid import UUID

from redis.exceptions import ResponseError

# Worker runs from the project root; make `app.*` importable.
sys.path.insert(0, "backend")

from app.core.logging import configure_logging, get_logger
from app.core.redis_client import close_redis
from app.db.session import dispose_engine, get_session_factory
from app.services.queue import CONSUMER_GROUP, STREAM_NAME, TaskQueue
from app.services.task_service import TaskService
from worker.config import get_worker_config
from worker.tasks.registry import TASK_REGISTRY

log = get_logger(__name__)

_shutdown = asyncio.Event()


def _install_signal_handlers() -> None:
    """Trigger graceful shutdown on SIGINT / SIGTERM."""
    loop = asyncio.get_event_loop()

    def _handler(sig: signal.Signals) -> None:
        log.info("worker_shutdown_requested", signal=sig.name)
        _shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            # Windows doesn't support add_signal_handler for all signals.
            # We fall back to KeyboardInterrupt for Ctrl+C, which works fine.
            loop.add_signal_handler(sig, _handler, sig)


async def _process_message(
    *,
    message_id: str,
    fields: dict[str, Any],
    queue: TaskQueue,
) -> None:
    """Execute a single task message and update the DB."""
    task_id_raw = fields.get("task_id")
    task_type = fields.get("type")
    payload_raw = fields.get("payload", "{}")

    if not isinstance(task_id_raw, str) or not isinstance(task_type, str):
        log.error("malformed_message", message_id=message_id, fields=fields)
        await queue.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
        return

    try:
        task_id = UUID(task_id_raw)
    except ValueError:
        log.error("invalid_task_id", message_id=message_id, raw=task_id_raw)
        await queue.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
        return

    try:
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else {}
        if not isinstance(payload, dict):
            payload = {}
    except json.JSONDecodeError:
        payload = {}

    log.info(
        "task_received",
        message_id=message_id,
        task_id=str(task_id),
        task_type=task_type,
    )

    handler = TASK_REGISTRY.get(task_type)
    if handler is None:
        error_msg = f"Unknown task type: {task_type!r}"
        log.error("unknown_task_type", message_id=message_id, task_type=task_type)
        factory = get_session_factory()
        async with factory() as session:
            service = TaskService(session)
            try:
                await service.mark_running(task_id)
                await service.mark_failed(task_id, error_msg)
            except ValueError as exc:
                log.warning("state_transition_failed", error=str(exc))
            await session.commit()
        await queue.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
        return

    factory = get_session_factory()
    async with factory() as session:
        service = TaskService(session)
        try:
            task = await service.mark_running(task_id)
            if task is None:
                log.warning("task_not_found", task_id=str(task_id))
                await session.commit()
                await queue.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
                return
            await session.commit()
        except ValueError as exc:
            log.warning("mark_running_failed", task_id=str(task_id), error=str(exc))
            await session.rollback()
            await queue.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
            return

    # Execute the handler OUTSIDE the DB transaction — it may take seconds,
    # and holding a session open that long is wasteful.
    try:
        result = await handler(payload)
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        log.exception("task_failed", task_id=str(task_id), task_type=task_type)
        async with factory() as session:
            service = TaskService(session)
            await service.mark_failed(task_id, error_msg)
            await session.commit()
        await queue.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
        return

    # Success path.
    async with factory() as session:
        service = TaskService(session)
        await service.mark_completed(task_id, result)
        await session.commit()

    log.info("task_completed", task_id=str(task_id), task_type=task_type)
    await queue.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)


async def _run_loop() -> None:
    """Main worker loop."""
    config = get_worker_config()
    log.info("worker_starting", consumer=config.consumer_name)

    queue = TaskQueue()
    await queue.ensure_group()

    log.info("worker_ready", consumer=config.consumer_name, stream=STREAM_NAME)

    while not _shutdown.is_set():
        try:
            response = await queue.redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=config.consumer_name,
                streams={STREAM_NAME: ">"},
                count=config.batch_size,
                block=config.block_ms,
            )
        except ResponseError as exc:
            log.error("xreadgroup_error", error=str(exc))
            await asyncio.sleep(1)
            continue
        except Exception as exc:
            log.exception("xreadgroup_unexpected", error=str(exc))
            await asyncio.sleep(1)
            continue

        if not response:
            continue

        for _stream_name, messages in response:
            for message_id, fields in messages:
                try:
                    await _process_message(
                        message_id=message_id,
                        fields=fields,
                        queue=queue,
                    )
                except Exception:
                    log.exception("message_processing_crashed", message_id=message_id)

    log.info("worker_stopped", consumer=config.consumer_name)
    await close_redis()
    await dispose_engine()


def main() -> None:
    """Entry point."""
    configure_logging(log_level="INFO", json_output=False)
    _install_signal_handlers()
    try:
        asyncio.run(_run_loop())
    except KeyboardInterrupt:
        log.info("worker_interrupted")


if __name__ == "__main__":
    main()
