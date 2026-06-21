from typing import Optional
from datetime import date

from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prospects import Prospect
from app.models.payments import Payment
from app.models.prospect_documents import ProspectDocument
from app.schemas import ProspectCreate, ProspectUpdate, ProspectOut
from app.core.config import settings


async def create_prospect(
    db: AsyncSession,
    data: ProspectCreate,
    created_by,
) -> Prospect:
    """Create a new prospect."""
    prospect = Prospect(
        name=data.name,
        email=data.email,
        phone=data.phone,
        stage=data.stage,
        course_name=data.course_name,
        course_id=data.course_id,
        father_name=data.father_name,
        mother_name=data.mother_name,
        dob=data.dob,
        specialization=data.specialization,
        address=data.address,
        delivery_address=data.delivery_address,
        delivery_date=data.delivery_date,
        estimated_value=data.estimated_value,
        notes=data.notes,
        created_by_id=created_by.user.id if created_by else None,
        employee_id=created_by.user.id if created_by else None,
    )
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)
    return prospect


async def get_prospect(db: AsyncSession, prospect_id: int) -> Optional[Prospect]:
    """Get prospect by ID with all relations."""
    result = await db.execute(
        select(Prospect)
        .where(Prospect.id == prospect_id)
        .options(
            selectinload(Prospect.payments),
            selectinload(Prospect.documents),
            selectinload(Prospect.timeline_events),
        )
    )
    return result.scalar_one_or_none()


async def get_prospect_out(db: AsyncSession, prospect_id: int) -> ProspectOut:
    """Get prospect with all related data serialized."""
    prospect = await get_prospect(db, prospect_id)
    if not prospect:
        return None
    
    # Calculate payment summary
    total_paid = sum(p.amount for p in prospect.payments) if prospect.payments else 0
    estimated = prospect.estimated_value or 0
    balance = max(estimated - total_paid, 0)
    
    # Determine payment status
    percentage = (total_paid / estimated * 100) if estimated > 0 else 0
    if percentage == 0:
        payment_status = "Not Paid"
    elif percentage < 50:
        payment_status = "Advance Paid"
    elif percentage < 100:
        payment_status = "Partially Paid"
    else:
        payment_status = "Fully Paid"
    
    return ProspectOut(
        id=prospect.id,
        name=prospect.name,
        email=prospect.email,
        phone=prospect.phone,
        stage=prospect.stage,
        course_name=prospect.course_name,
        course_id=prospect.course_id,
        father_name=prospect.father_name,
        mother_name=prospect.mother_name,
        dob=prospect.dob,
        specialization=prospect.specialization,
        address=prospect.address,
        delivery_address=prospect.delivery_address,
        delivery_date=prospect.delivery_date,
        estimated_value=prospect.estimated_value,
        notes=prospect.notes,
        exam_attended=prospect.exam_attended,
        exam_certified=prospect.exam_certified,
        created_at=prospect.created_at,
        updated_at=prospect.updated_at,
        # Relations
        payments=[
            {
                "id": p.id,
                "prospect_id": p.prospect_id,
                "amount": float(p.amount),
                "payment_type": p.payment_type,
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "receipt_url": p.receipt_url,
                "notes": p.notes,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in prospect.payments
        ],
        documents=[
            {
                "id": d.id,
                "prospect_id": d.prospect_id,
                "doc_type": d.doc_type,
                "file_url": d.file_url,
                "file_name": d.file_name,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in prospect.documents
        ],
        timeline_events=[
            {
                "id": t.id,
                "prospect_id": t.prospect_id,
                "type": t.type,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in prospect.timeline_events
        ],
        # Computed
        total_paid=total_paid,
        balance=balance,
        payment_status=payment_status,
        payment_percentage=min(round(percentage), 100),
    )


async def update_prospect(
    db: AsyncSession,
    prospect_id: int,
    data: ProspectUpdate,
) -> Prospect:
    """Update prospect fields."""
    prospect = await get_prospect(db, prospect_id)
    if not prospect:
        return None
    
    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(prospect, field, value)
    
    await db.commit()
    await db.refresh(prospect)
    return prospect


async def list_prospects(
    db: AsyncSession,
    employee_id: Optional[int] = None,
    search: Optional[str] = None,
    stage: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
):
    """List prospects with filtering and pagination."""
    query = select(Prospect).options(
        selectinload(Prospect.payments),
        selectinload(Prospect.documents),
    )
    
    if employee_id:
        query = query.where(Prospect.employee_id == employee_id)
    
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.where(
            or_(
                Prospect.name.ilike(search_lower),
                Prospect.email.ilike(search_lower),
                Prospect.phone.ilike(search_lower),
            )
        )
    
    if stage:
        query = query.where(Prospect.stage == stage)
    
    if date_from:
        query = query.where(Prospect.created_at >= date_from)
    if date_to:
        query = query.where(Prospect.created_at <= date_to)
    
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Build output
    prospect_outs = []
    for prospect in items:
        total_paid = sum(p.amount for p in prospect.payments) if prospect.payments else 0
        estimated = prospect.estimated_value or 0
        percentage = (total_paid / estimated * 100) if estimated > 0 else 0
        
        prospect_outs.append({
            "id": prospect.id,
            "name": prospect.name,
            "email": prospect.email,
            "phone": prospect.phone,
            "stage": prospect.stage,
            "course_name": prospect.course_name,
            "estimated_value": prospect.estimated_value,
            "total_paid": total_paid,
            "balance": max(estimated - total_paid, 0),
            "payment_status": "Fully Paid" if percentage >= 100 else "Partially Paid" if percentage > 0 else "Not Paid",
            "created_at": prospect.created_at.isoformat() if prospect.created_at else None,
        })
    
    return {
        "data": prospect_outs,
        "items": prospect_outs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pageSize": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "totalPages": (total + page_size - 1) // page_size,
    }