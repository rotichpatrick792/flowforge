"""Async Redis client, lazily initialized and shared across the app."""

from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """Return the process-wide Redis client, creating it on first use."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    """Close the client. Call on application shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
