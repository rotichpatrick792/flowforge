import asyncio
import sys

sys.path.insert(0, "backend")

from sqlalchemy import text  # noqa: E402

from app.db.session import get_engine  # noqa: E402


async def main() -> None:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        value = result.scalar()
        print("DB connection OK:", value)


if __name__ == "__main__":
    asyncio.run(main())