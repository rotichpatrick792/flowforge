"""Redis Streams-backed task queue.

The stream `flowforge:tasks` holds task events. Workers join the consumer
group `flowforge:workers` and read messages with `XREADGROUP`. Each message
is delivered to exactly one consumer in the group.

Delivery semantics: **at-least-once**. A message is redelivered if a worker
picks it up but never ACKs it (crash, timeout). Consumers must therefore be
idempotent — Phase 4 formalizes this with task-level idempotency keys.
"""

import json
from typing import Any, cast
from uuid import UUID

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.core.redis_client import get_redis

STREAM_NAME = "flowforge:tasks"
CONSUMER_GROUP = "flowforge:workers"

# Cap stream length so it doesn't grow unbounded. ~ means "approximate"
# which lets Redis trim lazily and stay fast.
STREAM_MAXLEN = 10_000

log = get_logger(__name__)


class TaskQueue:
    """Thin wrapper around the Redis Stream used as FlowForge's job queue."""

    def __init__(self, redis: Redis | None = None) -> None:
        # Allow callers (tests) to inject a client; default to the app's.
        self._redis = redis

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def ensure_group(self) -> None:
        """Create the consumer group if it doesn't exist.

        Safe to call on every startup. `mkstream=True` creates the stream
        if it's empty (Redis Streams don't exist until something is added).

        We use `id="0"` so the group sees all messages from the beginning
        the first time it's created. On subsequent calls, the group already
        exists and this is a no-op.
        """
        try:
            await self.redis.xgroup_create(
                name=STREAM_NAME,
                groupname=CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )
            log.info("queue_group_created", stream=STREAM_NAME, group=CONSUMER_GROUP)
        except Exception as exc:
            # Redis raises ResponseError with "BUSYGROUP" when the group exists.
            if "BUSYGROUP" in str(exc):
                log.debug("queue_group_exists", stream=STREAM_NAME, group=CONSUMER_GROUP)
            else:
                raise

    async def enqueue(
        self,
        *,
        task_id: UUID,
        type: str,
        payload: dict[str, Any],
    ) -> str:
        """Append a task event to the stream. Returns the message ID.

        NOTE: This is a best-effort publish. If Redis is unavailable, the
        caller must decide whether to fail the request or proceed. In
        Phase 2's POST handler we currently *do* fail the request (Redis
        down == 503) because we don't yet have a reconciliation sweep. A
        future phase will add that sweep and downgrade this to best-effort.
        """
        message_id = await self.redis.xadd(
            name=STREAM_NAME,
            fields={
                "task_id": str(task_id),
                "type": type,
                "payload": json.dumps(payload),
            },
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )
        log.info(
            "task_enqueued",
            stream=STREAM_NAME,
            message_id=message_id,
            task_id=str(task_id),
            task_type=type,
        )
        return cast(str, message_id)
