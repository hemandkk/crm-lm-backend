from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Employee, Prospect, Payment, IncentiveSlab
from app.schemas import (
    AdminDashboardOut,
    EmployeeDashboardOut,
    MonthlyRevenueOut,
    StageCountOut,
    ExamStatsOut,
    IncentiveStatusOut,
    PaymentSummaryOut,
)
from app.services.employee_service import get_performance
from app.services.incentive_service import calculate_incentive
from app.services.payment_service import get_payment_summary


async def get_admin_dashboard(
    db: AsyncSession,
    employee_id: Optional[UUID] = None,
) -> AdminDashboardOut:
    tz = timezone.utc
    now = datetime.now(tz)

    # ── Counts ────────────────────────────────────────────────────────────
    emp_count_result = await db.execute(
        select(func.count()).select_from(Employee).where(Employee.status == "active")
    )
    total_employees = emp_count_result.scalar_one()

    prospect_q = select(func.count()).select_from(Prospect)
    if employee_id:
        prospect_q = prospect_q.where(Prospect.assigned_to == employee_id)
    total_leads = (await db.execute(prospect_q)).scalar_one()

    revenue_q = select(func.coalesce(func.sum(Payment.amount), 0))
    if employee_id:
        revenue_q = revenue_q.where(Payment.created_by == employee_id)
    total_revenue = float((await db.execute(revenue_q)).scalar_one())

    # Conversion rate = won / total
    won_q = select(func.count()).select_from(Prospect).where(Prospect.stage == "won")
    if employee_id:
        won_q = won_q.where(Prospect.assigned_to == employee_id)
    total_won = (await db.execute(won_q)).scalar_one()
    conversion_rate = round((total_won / total_leads * 100) if total_leads else 0, 1)

    certs_q = select(func.count()).select_from(Prospect).where(Prospect.exam_certified.is_(True))
    if employee_id:
        certs_q = certs_q.where(Prospect.assigned_to == employee_id)
    certificates_issued = (await db.execute(certs_q)).scalar_one()

    # ── Leads this period ─────────────────────────────────────────────────
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async def _lead_count(since: datetime) -> int:
        q = select(func.count()).select_from(Prospect).where(Prospect.created_at >= since)
        if employee_id:
            q = q.where(Prospect.assigned_to == employee_id)
        return (await db.execute(q)).scalar_one()

    leads_today = await _lead_count(today_start)
    leads_this_week = await _lead_count(week_start)
    leads_this_month = await _lead_count(month_start)

    # ── Revenue by month (last 6 months) ─────────────────────────────────
    revenue_by_month: list[MonthlyRevenueOut] = []
    for i in range(5, -1, -1):
        d = now.replace(day=1) - timedelta(days=i * 28)
        m_start = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            m_end = now
        else:
            next_m = (m_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            m_end = next_m - timedelta(seconds=1)

        rev_q = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.payment_date >= m_start, Payment.payment_date <= m_end
        )
        if employee_id:
            rev_q = rev_q.where(Payment.created_by == employee_id)
        rev = float((await db.execute(rev_q)).scalar_one())

        cnt_q = select(func.count()).select_from(Prospect).where(
            Prospect.created_at >= m_start, Prospect.created_at <= m_end
        )
        if employee_id:
            cnt_q = cnt_q.where(Prospect.assigned_to == employee_id)
        cnt = (await db.execute(cnt_q)).scalar_one()

        revenue_by_month.append(MonthlyRevenueOut(
            month=m_start.strftime("%b %Y"),
            revenue=rev,
            leads_count=cnt,
        ))

    # ── Leads by stage ────────────────────────────────────────────────────
    stage_q = select(Prospect.stage, func.count()).group_by(Prospect.stage)
    if employee_id:
        stage_q = stage_q.where(Prospect.assigned_to == employee_id)
    stage_result = await db.execute(stage_q)
    leads_by_stage = [
        StageCountOut(stage=row[0], count=row[1])
        for row in stage_result.all()
    ]

    # ── Employee performance ──────────────────────────────────────────────
    emp_result = await db.execute(
        select(Employee).where(Employee.status == "active").limit(50)
    )
    employees = emp_result.scalars().all()

    perf_list = []
    for emp in employees:
        try:
            perf = await get_performance(db, emp.id)
            perf_list.append(perf)
        except Exception:
            pass

    top_performers = sorted(perf_list, key=lambda x: x.total_revenue, reverse=True)[:5]

    return AdminDashboardOut(
        total_employees=total_employees,
        total_leads=total_leads,
        total_revenue=total_revenue,
        conversion_rate=conversion_rate,
        certificates_issued=certificates_issued,
        leads_this_month=leads_this_month,
        leads_this_week=leads_this_week,
        leads_today=leads_today,
        revenue_by_month=revenue_by_month,
        leads_by_stage=leads_by_stage,
        employee_performance=perf_list,
        top_performers=top_performers,
    )


async def get_employee_dashboard(
    db: AsyncSession,
    employee: Employee,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> EmployeeDashboardOut:
    tz = timezone.utc
    now = datetime.now(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ── Lead counts ───────────────────────────────────────────────────────
    async def _lead_count(since: datetime, until: Optional[datetime] = None) -> int:
        q = select(func.count()).select_from(Prospect).where(
            Prospect.assigned_to == employee.id,
            Prospect.created_at >= since,
        )
        if until:
            q = q.where(Prospect.created_at <= until)
        return (await db.execute(q)).scalar_one()

    total_leads_result = await db.execute(
        select(func.count()).select_from(Prospect).where(Prospect.assigned_to == employee.id)
    )
    total_leads = total_leads_result.scalar_one()
    leads_this_month = await _lead_count(month_start)
    leads_this_week = await _lead_count(week_start)
    leads_today = await _lead_count(today_start)

    # ── Target this month ─────────────────────────────────────────────────
    target_achieved = leads_this_month
    target = employee.monthly_target
    ratio = target_achieved / target if target else 0
    if ratio >= 1.2:
        target_status = "excellent"
    elif ratio >= 1.0:
        target_status = "met"
    elif ratio >= 0.5:
        target_status = "on_track"
    else:
        target_status = "behind"

    # ── Payment summary ───────────────────────────────────────────────────
    payment_summary = await get_payment_summary(db, employee_id=employee.id)

    # ── Incentive ─────────────────────────────────────────────────────────
    slabs_result = await db.execute(
        select(IncentiveSlab).order_by(IncentiveSlab.min_amount)
    )
    slabs = slabs_result.scalars().all()
    incentive_raw = calculate_incentive(payment_summary.this_month, slabs)
    incentive = IncentiveStatusOut(**incentive_raw)

    # ── Exam stats ────────────────────────────────────────────────────────
    attended_result = await db.execute(
        select(func.count()).select_from(Prospect).where(
            Prospect.assigned_to == employee.id,
            Prospect.exam_attended.is_(True),
        )
    )
    certified_result = await db.execute(
        select(func.count()).select_from(Prospect).where(
            Prospect.assigned_to == employee.id,
            Prospect.exam_certified.is_(True),
        )
    )

    return EmployeeDashboardOut(
        total_leads=total_leads,
        leads_this_month=leads_this_month,
        leads_this_week=leads_this_week,
        leads_today=leads_today,
        monthly_target=target,
        target_achieved=target_achieved,
        target_status=target_status,
        payment_summary=payment_summary,
        incentive=incentive,
        exam_stats=ExamStatsOut(
            attended=attended_result.scalar_one(),
            certified=certified_result.scalar_one(),
        ),
    )