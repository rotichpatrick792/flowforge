"""Task API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskListResponse, TaskRead
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new task",
)
async def create_task(
    data: TaskCreate,
    session: DbSession,
) -> TaskRead:
    """Accept a task, persist it as `pending`, return it."""
    service = TaskService(session)
    task = await service.create(data)
    return TaskRead.model_validate(task)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
)
async def list_tasks(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
) -> TaskListResponse:
    """Return a page of tasks, newest first, optionally filtered by status."""
    service = TaskService(session)
    items, total = await service.list(limit=limit, offset=offset, status=status_filter)
    return TaskListResponse(
        items=[TaskRead.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Fetch a task by ID",
)
async def get_task(
    task_id: UUID,
    session: DbSession,
) -> TaskRead:
    """Return the task with the given ID, or 404."""
    service = TaskService(session)
    task = await service.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return TaskRead.model_validate(task)
