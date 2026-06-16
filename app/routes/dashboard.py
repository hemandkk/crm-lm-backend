from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentAdmin, CurrentEmployee, DBSession
from app.schemas import AdminDashboardOut, EmployeeDashboardOut
from app.services import dashboard_service

router = APIRouter(tags=["Dashboard"])


@router.get("/admin", response_model=AdminDashboardOut)
async def admin_dashboard(
    db: DBSession,
    _: CurrentAdmin,
    employee_id: Optional[UUID] = Query(None),
):
    return await dashboard_service.get_admin_dashboard(db, employee_id=employee_id)


@router.get("/employee", response_model=EmployeeDashboardOut)
async def employee_dashboard(
    db: DBSession,
    current_employee: CurrentEmployee,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    tz = timezone.utc
    df = datetime.fromisoformat(date_from).replace(tzinfo=tz) if date_from else None
    dt = datetime.fromisoformat(date_to).replace(tzinfo=tz) if date_to else None

    return await dashboard_service.get_employee_dashboard(
        db, current_employee, date_from=df, date_to=dt
    )