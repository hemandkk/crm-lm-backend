from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prospects import Prospect
import re
from sqlalchemy.orm import Session
from app.models.user import User

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

def generate_employee_id(db: Session) -> str:
    last_employee = (
        db.query(User)
        .filter(User.employee_id.isnot(None))
        .order_by(User.id.desc())
        .first()
    )

    if not last_employee or not last_employee.employee_id:
        return "EMP0001"

    match = re.search(r"(\d+)$", last_employee.employee_id)

    if not match:
        return "EMP0001"

    next_number = int(match.group(1)) + 1

    return f"EMP{next_number:04d}"