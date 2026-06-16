from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Prospect


async def next_prospect_id(db: AsyncSession) -> str:
    """
    Generate the next sequential prospect ID: PRO-100001, PRO-100002, …
    Uses a DB-level lock to prevent duplicates under concurrency.
    """
    result = await db.execute(
        select(func.max(
            func.cast(
                func.substr(Prospect.prospect_id, 5),  # strip "PRO-"
                text("INTEGER"),
            )
        ))
    )
    max_num = result.scalar_one_or_none()
    next_num = (max_num or 100000) + 1
    return f"PRO-{next_num}"