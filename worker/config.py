"""Worker-specific configuration."""

import os
import socket
from dataclasses import dataclass


def _default_consumer_name() -> str:
    """Unique per worker process: hostname + PID."""
    return f"{socket.gethostname()}-{os.getpid()}"


@dataclass(frozen=True)
class WorkerConfig:
    """Runtime configuration for a single worker process."""

    consumer_name: str
    batch_size: int = 1
    block_ms: int = 5_000
    """How long XREADGROUP blocks waiting for new messages (ms)."""


def get_worker_config() -> WorkerConfig:
    """Build the worker config, honoring WORKER_CONSUMER_NAME if set."""
    name = os.environ.get("WORKER_CONSUMER_NAME") or _default_consumer_name()
    return WorkerConfig(consumer_name=name)
