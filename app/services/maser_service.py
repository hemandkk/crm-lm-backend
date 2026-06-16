from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException

from app.models import Course, IncentiveSlab
from app.schemas import CourseCreate, IncentiveSlabCreate, CourseOut, IncentiveSlabOut


async def list_courses(db: AsyncSession) -> list[CourseOut]:
    result = await db.execute(
        select(Course).where(Course.active.is_(True)).order_by(Course.name)
    )
    return [CourseOut.model_validate(c) for c in result.scalars().all()]


async def create_course(db: AsyncSession, data: CourseCreate) -> CourseOut:
    existing = await db.execute(select(Course).where(Course.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Course already exists")

    course = Course(name=data.name)
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return CourseOut.model_validate(course)


async def delete_course(db: AsyncSession, course_id: str) -> None:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.active = False  # soft delete
    await db.flush()


async def list_incentive_slabs(db: AsyncSession) -> list[IncentiveSlabOut]:
    result = await db.execute(
        select(IncentiveSlab).order_by(IncentiveSlab.min_amount)
    )
    return [IncentiveSlabOut.model_validate(s) for s in result.scalars().all()]


async def update_incentive_slabs(
    db: AsyncSession, slabs: list[IncentiveSlabCreate]
) -> list[IncentiveSlabOut]:
    # Replace all slabs atomically
    await db.execute(delete(IncentiveSlab))
    new_slabs = []
    for slab in slabs:
        s = IncentiveSlab(
            min_amount=slab.min_amount,
            max_amount=slab.max_amount,
            rate_percent=slab.rate_percent,
        )
        db.add(s)
        new_slabs.append(s)

    await db.flush()
    for s in new_slabs:
        await db.refresh(s)

    return [IncentiveSlabOut.model_validate(s) for s in new_slabs]


async def set_employee_target(
    db: AsyncSession, employee_id: str, target: int
) -> None:
    from app.models import Employee
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.monthly_target = target
    await db.flush()