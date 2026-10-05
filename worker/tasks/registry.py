"""Registry of safe, whitelisted task handlers.

Workers execute ONLY functions from this registry. Adding a task type
means adding a function here and registering it. There is no mechanism
for executing arbitrary user-supplied code, shell commands, or scripts.

Each handler:
- is async
- takes a single `payload: dict` argument
- returns a JSON-serializable `dict` result
- raises on invalid input (the worker will record the failure)
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

TaskHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


async def echo(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the payload unchanged. Proves the pipeline works end-to-end."""
    return {"echo": payload}


async def add(payload: dict[str, Any]) -> dict[str, Any]:
    """Add two numbers from the payload.

    Expected payload: {"a": <number>, "b": <number>}
    """
    a = payload.get("a")
    b = payload.get("b")

    if not isinstance(a, int | float) or not isinstance(b, int | float):
        raise ValueError("Payload must contain numeric 'a' and 'b' fields")

    return {"sum": a + b}


async def sleep(payload: dict[str, Any]) -> dict[str, Any]:
    """Await for the requested number of seconds.

    Expected payload: {"seconds": <number>}
    Used to prove long-running tasks behave correctly.
    """
    seconds = payload.get("seconds")

    if not isinstance(seconds, int | float):
        raise ValueError("Payload must contain a numeric 'seconds' field")
    if seconds < 0 or seconds > 60:
        raise ValueError("'seconds' must be between 0 and 60")

    await asyncio.sleep(seconds)
    return {"slept": seconds}


TASK_REGISTRY: dict[str, TaskHandler] = {
    "echo": echo,
    "add": add,
    "sleep": sleep,
}
