import os
import uuid
from datetime import date
from typing import Optional
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Prospect
from app.schemas import PaymentCreate, PaymentSummaryOut
from app.core.config import settings


async def create_payment(
    db: AsyncSession,
    data: PaymentCreate,
    created_by,
    receipt: Optional[UploadFile] = None,
) -> Payment:
    """Create a payment. If receipt provided, save it."""
    payment = Payment(
        prospect_id=data.prospect_id,
        amount=data.amount,
        payment_type=data.payment_type,
        payment_date=data.payment_date,
        notes=data.notes,
        created_by_id=created_by.user.id if created_by else None,
    )
    
    # Handle receipt upload
    if receipt and receipt.filename and receipt.size > 0:
        receipt_url = await _save_receipt_file(receipt)
        payment.receipt_url = receipt_url
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def upload_receipt(
    db: AsyncSession,
    payment: Payment,
    receipt: UploadFile,
) -> Payment:
    """Phase 2: Upload receipt to existing payment."""
    receipt_url = await _save_receipt_file(receipt)
    payment.receipt_url = receipt_url
    await db.commit()
    await db.refresh(payment)
    return payment


async def get_payment(db: AsyncSession, payment_id: int) -> Optional[Payment]:
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    return result.scalar_one_or_none()


async def delete_payments_by_prospect(db: AsyncSession, prospect_id: int) -> None:
    """Delete all payments for a prospect (used during update replacement)."""
    await db.execute(
        delete(Payment).where(Payment.prospect_id == prospect_id)
    )
    await db.commit()


async def list_payments(
    db: AsyncSession,
    employee_id: Optional[int] = None,
    prospect_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
):
    """List payments with filtering."""
    query = select(Payment).join(Prospect)
    
    if employee_id:
        query = query.where(Prospect.employee_id == employee_id)
    if prospect_id:
        query = query.where(Payment.prospect_id == prospect_id)
    if date_from:
        query = query.where(Payment.payment_date >= date_from)
    if date_to:
        query = query.where(Payment.payment_date <= date_to)
    
    # Count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {
        "data": items,
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pageSize": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "totalPages": (total + page_size - 1) // page_size,
    }


async def get_payment_summary(
    db: AsyncSession,
    employee_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Get payment summary statistics."""
    query = select(
        func.count(Payment.id).label("total_payments"),
        func.sum(Payment.amount).label("total_amount"),
    ).select_from(Payment).join(Prospect)
    
    if employee_id:
        query = query.where(Prospect.employee_id == employee_id)
    if date_from:
        query = query.where(Payment.payment_date >= date_from)
    if date_to:
        query = query.where(Payment.payment_date <= date_to)
    
    result = await db.execute(query)
    row = result.one()
    
    # By payment type
    type_query = select(
        Payment.payment_type,
        func.count(Payment.id).label("count"),
        func.sum(Payment.amount).label("amount"),
    ).select_from(Payment).join(Prospect)
    
    if employee_id:
        type_query = type_query.where(Prospect.employee_id == employee_id)
    if date_from:
        type_query = type_query.where(Payment.payment_date >= date_from)
    if date_to:
        type_query = type_query.where(Payment.payment_date <= date_to)
    
    type_query = type_query.group_by(Payment.payment_type)
    type_result = await db.execute(type_query)
    by_type = {row.payment_type: {"count": row.count, "amount": float(row.amount)} for row in type_result}
    
    return {
        "total_payments": row.total_payments or 0,
        "total_amount": float(row.total_amount) if row.total_amount else 0,
        "by_type": by_type,
    }


async def _save_receipt_file(receipt: UploadFile) -> str:
    """Save receipt file and return URL."""
    ext = os.path.splitext(receipt.filename or "receipt.pdf")[1]
    filename = f"{uuid.uuid4()}{ext}"
    
    upload_dir = os.path.join(settings.UPLOAD_DIR, "receipts")
    os.makedirs(upload_dir, exist_ok=True)
    
    filepath = os.path.join(upload_dir, filename)
    
    contents = await receipt.read()
    with open(filepath, "wb") as f:
        f.write(contents)
    
    return f"/uploads/receipts/{filename}"