"""Task business logic. No HTTP, no FastAPI — just operations on the DB."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate


class TaskService:
    """Encapsulates task-related DB operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: TaskCreate) -> Task:
        """Insert a new pending task and return it."""
        task = Task(
            type=data.type,
            payload=data.payload,
            status=TaskStatus.PENDING,
        )
        self.session.add(task)
        await self.session.flush()  # assign server-generated values (id, timestamps)
        await self.session.refresh(task)
        return task

    async def get(self, task_id: UUID) -> Task | None:
        """Fetch a single task by ID, or None."""
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: TaskStatus | None = None,
    ) -> tuple[list[Task], int]:
        """Return a page of tasks and the total count matching the filter."""
        base = select(Task)
        count_stmt = select(func.count()).select_from(Task)

        if status is not None:
            base = base.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)

        base = base.order_by(Task.created_at.desc()).limit(limit).offset(offset)

        items_result = await self.session.execute(base)
        items = list(items_result.scalars().all())

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        return items, total
