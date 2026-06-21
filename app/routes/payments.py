from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.core.deps import CurrentEmployee, CurrentAdmin, CurrentAnyUser, DBSession
from app.schemas import PaymentCreate, PaymentOut, PaymentSummaryOut, PaginatedResponse
from app.services import payment_service

router = APIRouter(tags=["Payments"])


@router.get("", response_model=PaginatedResponse[PaymentOut])
async def list_payments(
    db: DBSession,
    current_user: CurrentAnyUser,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    prospect_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    # Employees see only their own payments
    employee_id = None
    if current_user.user_type == "employee":
        employee_id = current_user.user.id

    return await payment_service.list_payments(
        db,
        employee_id=employee_id,
        prospect_id=prospect_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(
    db: DBSession,
    current_employee: CurrentEmployee,
    prospect_id: UUID = Form(...),
    amount: float = Form(...),
    payment_type: str = Form(...),
    payment_date: date = Form(...),
    notes: Optional[str] = Form(None),
    receipt: Optional[UploadFile] = File(None),
):
    from decimal import Decimal
    data = PaymentCreate(
        prospect_id=prospect_id,
        amount=Decimal(str(amount)),
        payment_type=payment_type,  # type: ignore[arg-type]
        payment_date=payment_date,
        notes=notes,
    )
    payment = await payment_service.create_payment(db, data, current_employee, receipt)
    return PaymentOut(
        id=payment.id,
        prospect_id=payment.prospect_id,
        amount=float(payment.amount),
        payment_type=payment.payment_type,
        payment_date=payment.payment_date,
        receipt_url=payment.receipt_url,
        notes=payment.notes,
        created_by=payment.created_by,
        created_at=payment.created_at,
    )


@router.get("/summary", response_model=PaymentSummaryOut)
async def get_summary(
    db: DBSession,
    current_user: CurrentAnyUser,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    employee_id = None
    if current_user.user_type == "employee":
        employee_id = current_user.user.id

    return await payment_service.get_payment_summary(
        db,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )


""" 
async def list_payments(
    db: DBSession,
    current_user: CurrentAnyUser,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    prospect_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    employee_id = None
    if current_user.user_type == "employee":
        employee_id = current_user.user.id

    return await payment_service.list_payments(
        db,
        employee_id=employee_id,
        prospect_id=prospect_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(
    db: DBSession,
    current_employee: CurrentEmployee,
    prospect_id: UUID = Form(...),
    amount: float = Form(...),
    payment_type: str = Form(...),
    payment_date: date = Form(...),
    notes: Optional[str] = Form(None),
    receipt: Optional[UploadFile] = File(None),
):
    from decimal import Decimal
    data = PaymentCreate(
        prospect_id=prospect_id,
        amount=Decimal(str(amount)),
        payment_type=payment_type,
        payment_date=payment_date,
        notes=notes,
    )
    payment = await payment_service.create_payment(db, data, current_employee, receipt)
    return PaymentOut(
        id=payment.id,
        prospect_id=payment.prospect_id,
        amount=float(payment.amount),
        payment_type=payment.payment_type,
        payment_date=payment.payment_date,
        receipt_url=payment.receipt_url,
        notes=payment.notes,
        created_by=payment.created_by,
        created_at=payment.created_at,
    )


# ─── Phase 2: Upload receipt to existing payment ─────────────────

@router.post("/{payment_id}/receipt", response_model=PaymentOut)
async def upload_payment_receipt(
    db: DBSession,
    current_employee: CurrentEmployee,
    payment_id: int,
    receipt: UploadFile = File(...),
):
    """Upload receipt to an existing payment (two-phase upload)."""
    payment = await payment_service.get_payment(db, payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Optional: verify employee owns this payment or has access
    # if current_user.user_type == "employee" and payment.created_by_id != current_user.user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    updated = await payment_service.upload_receipt(db, payment, receipt)
    return PaymentOut(
        id=updated.id,
        prospect_id=updated.prospect_id,
        amount=float(updated.amount),
        payment_type=updated.payment_type,
        payment_date=updated.payment_date,
        receipt_url=updated.receipt_url,
        notes=updated.notes,
        created_by=updated.created_by,
        created_at=updated.created_at,
    )


@router.get("/summary", response_model=PaymentSummaryOut)
async def get_summary(
    db: DBSession,
    current_user: CurrentAnyUser,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    employee_id = None
    if current_user.user_type == "employee":
        employee_id = current_user.user.id

    return await payment_service.get_payment_summary(
        db,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )

 """