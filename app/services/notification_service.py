from datetime import datetime, date, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog, Notification
from app.schemas import (
    ActivityLogOut,
    NotificationOut,
    PaginatedResponse,
)


# ── Activity logs ─────────────────────────────────────────────────────────────
async def list_activity_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PaginatedResponse[ActivityLogOut]:
    tz = timezone.utc
    query = select(ActivityLog)

    if action:
        query = query.where(ActivityLog.action == action)
    if user_id:
        query = query.where(ActivityLog.user_id == user_id)
    if date_from:
        dt_from = datetime.combine(date_from, datetime.min.time()).replace(tzinfo=tz)
        query = query.where(ActivityLog.created_at >= dt_from)
    if date_to:
        dt_to = datetime.combine(date_to, datetime.max.time()).replace(tzinfo=tz)
        query = query.where(ActivityLog.created_at <= dt_to)

    subq = query.with_only_columns(ActivityLog.id).subquery()
    total = (await db.execute(select(func.count()).select_from(subq))).scalar_one()

    query = query.order_by(ActivityLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return PaginatedResponse(
        data=[ActivityLogOut.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


async def write_log(
    db: AsyncSession,
    *,
    user_id: Optional[str],
    user_name: Optional[str],
    user_type: Optional[str],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    db.add(
        ActivityLog(
            user_id=user_id,
            user_name=user_name,
            user_type=user_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            ip_address=ip_address,
        )
    )


# ── Notifications ─────────────────────────────────────────────────────────────
async def get_notifications(
    db: AsyncSession, employee_id: UUID
) -> list[NotificationOut]:
    result = await db.execute(
        select(Notification)
        .where(Notification.employee_id == employee_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]


async def mark_notification_read(
    db: AsyncSession, notification_id: UUID, employee_id: UUID
) -> None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.employee_id == employee_id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif:
        notif.read = True
        await db.flush()


async def mark_all_notifications_read(
    db: AsyncSession, employee_id: UUID
) -> None:
    result = await db.execute(
        select(Notification).where(
            Notification.employee_id == employee_id,
            Notification.read.is_(False),
        )
    )
    for n in result.scalars().all():
        n.read = True
    await db.flush()


async def send_notification(
    db: AsyncSession,
    employee_id: UUID,
    title: str,
    body: str,
) -> None:
    db.add(
        Notification(
            employee_id=employee_id,
            title=title,
            body=body,
        )
    )