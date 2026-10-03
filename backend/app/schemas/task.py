"""Pydantic schemas for the Task API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    """Payload for POST /tasks."""

    type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskRead(BaseModel):
    """Serialized task returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    status: TaskStatus
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    attempts: int
    max_attempts: int
    run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""

    items: list[TaskRead]
    total: int
    limit: int
    offset: int
