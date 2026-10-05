"""Task API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskListResponse, TaskRead
from app.services.queue import TaskQueue
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
    """Accept a task, persist it as `pending`, enqueue it, and return it.

    Both the DB insert and the queue publish must succeed. If the queue
    publish fails, the DB transaction is rolled back by the `get_db`
    dependency (it rolls back on exception), and the client sees a 5xx.

    This is a deliberate choice for Phase 3: consistency over availability.
    Phase 4 will add a reconciliation sweep so we can relax the DB write
    to best-effort and rely on the sweep to re-enqueue orphans.
    """
    service = TaskService(session)
    task = await service.create(data)

    # Commit BEFORE enqueueing so the worker can always find the task.
    # Otherwise the worker races with our transaction commit and may
    # see "task not found" for a task that's about to be committed.
    # See ADR 0004 for the failure modes and the reconciliation plan.
    await session.commit()

    queue = TaskQueue()
    await queue.enqueue(
        task_id=task.id,
        type=task.type,
        payload=task.payload,
    )

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
