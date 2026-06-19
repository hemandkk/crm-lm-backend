from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
import json

from app.core.deps import CurrentEmployee, CurrentAnyUser, DBSession
from app.schemas import (
    ProspectCreate,
    ProspectUpdate,
    ProspectOut,
    PaginatedResponse,
    PaymentCreate,
    PaymentOut,
)
from app.services import prospect_service, payment_service

router = APIRouter(tags=["Prospects"])


# ─── Inline Payment Parsing ──────────────────────────────────────

def _parse_inline_payments(payments_json: Optional[str]) -> list[PaymentCreate]:
    """Parse JSON string of payments into PaymentCreate objects."""
    if not payments_json:
        return []
    
    try:
        data = json.loads(payments_json)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in payments field"
        )
    
    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payments must be a JSON array"
        )
    
    payments = []
    for item in data:
        try:
            payment = PaymentCreate(
                prospect_id=0,  # Will be set after prospect creation
                amount=item["amount"],
                payment_type=item["paymentType"],
                payment_date=datetime.strptime(item["paymentDate"], "%Y-%m-%d").date(),
                notes=item.get("notes"),
            )
            payments.append(payment)
        except (KeyError, ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment data: {str(e)}"
            )
    
    return payments


# ─── List Prospects ──────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[ProspectOut])
async def list_prospects(
    db: DBSession,
    current_user: CurrentAnyUser,
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    employee_id = None
    if current_user.user_type == "employee":
        employee_id = current_user.user.id

    return await prospect_service.list_prospects(
        db,
        employee_id=employee_id,
        search=search,
        stage=stage,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


# ─── Create Prospect (with inline payments) ──────────────────────

@router.post("", response_model=ProspectOut, status_code=201)
async def create_prospect(
    db: DBSession,
    current_employee: CurrentEmployee,
    # ── Prospect fields ──
    name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    stage: str = Form("new"),
    course_name: Optional[str] = Form(None, alias="courseName"),
    course_id: Optional[str] = Form(None, alias="courseId"),
    father_name: Optional[str] = Form(None, alias="fatherName"),
    mother_name: Optional[str] = Form(None, alias="motherName"),
    dob: Optional[str] = Form(None),
    specialization: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    delivery_address: Optional[str] = Form(None, alias="deliveryAddress"),
    delivery_date: Optional[str] = Form(None, alias="deliveryDate"),
    estimated_value: Optional[float] = Form(None, alias="estimatedValue"),
    notes: Optional[str] = Form(None),
    # ── Inline payments ──
    payments_json: Optional[str] = Form(None, alias="payments"),
    # ── Payment receipts (indexed by order in payments array) ──
    payment_receipts: List[UploadFile] = File(default=[]),
):
    # Parse inline payments
    payment_creates = _parse_inline_payments(payments_json)
    
    # Validate receipt count matches payment count
    receipt_count = sum(1 for p in payment_creates if p.notes)  # Actually, we need to track which has receipt
    # Better: track receipt indices in frontend, or just allow extra receipts
    
    # 1. Create prospect
    prospect_data = ProspectCreate(
        name=name,
        email=email,
        phone=phone,
        stage=stage,
        course_name=course_name,
        course_id=course_id,
        father_name=father_name,
        mother_name=mother_name,
        dob=dob,
        specialization=specialization,
        address=address,
        delivery_address=delivery_address,
        delivery_date=delivery_date,
        estimated_value=estimated_value,
        notes=notes,
    )
    
    prospect = await prospect_service.create_prospect(
        db, prospect_data, current_employee
    )
    
    # 2. Create payments with receipts
    for i, payment_data in enumerate(payment_creates):
        payment_data.prospect_id = prospect.id  # Set actual prospect ID
        
        receipt = payment_receipts[i] if i < len(payment_receipts) else None
        # Only use receipt if it's actually a file (not empty)
        if receipt and receipt.filename and receipt.size > 0:
            pass  # receipt is valid
        else:
            receipt = None
        
        await payment_service.create_payment(
            db, payment_data, current_employee, receipt
        )
    
    # 3. Refresh and return with all relations
    await db.refresh(prospect)
    return await prospect_service.get_prospect_out(db, prospect.id)


# ─── Get Prospect ────────────────────────────────────────────────

@router.get("/{prospect_id}", response_model=ProspectOut)
async def get_prospect(
    db: DBSession,
    current_user: CurrentAnyUser,
    prospect_id: int,
):
    prospect = await prospect_service.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return await prospect_service.get_prospect_out(db, prospect_id)


# ─── Update Prospect ───────────────────────────────────────────

@router.put("/{prospect_id}", response_model=ProspectOut)
async def update_prospect(
    db: DBSession,
    current_employee: CurrentEmployee,
    prospect_id: int,
    # ── All fields as Form (optional for partial update) ──
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    stage: Optional[str] = Form(None),
    course_name: Optional[str] = Form(None, alias="courseName"),
    course_id: Optional[str] = Form(None, alias="courseId"),
    father_name: Optional[str] = Form(None, alias="fatherName"),
    mother_name: Optional[str] = Form(None, alias="motherName"),
    dob: Optional[str] = Form(None),
    specialization: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    delivery_address: Optional[str] = Form(None, alias="deliveryAddress"),
    delivery_date: Optional[str] = Form(None, alias="deliveryDate"),
    estimated_value: Optional[float] = Form(None, alias="estimatedValue"),
    notes: Optional[str] = Form(None),
    exam_attended: Optional[bool] = Form(None, alias="examAttended"),
    exam_certified: Optional[bool] = Form(None, alias="examCertified"),
    # ── Replace payments flag ──
    replace_payments: bool = Form(False, alias="replacePayments"),
    payments_json: Optional[str] = Form(None, alias="payments"),
    payment_receipts: List[UploadFile] = File(default=[]),
):
    # Build update data (exclude None values)
    update_data = {
        k: v for k, v in {
            "name": name,
            "email": email,
            "phone": phone,
            "stage": stage,
            "course_name": course_name,
            "course_id": course_id,
            "father_name": father_name,
            "mother_name": mother_name,
            "dob": dob,
            "specialization": specialization,
            "address": address,
            "delivery_address": delivery_address,
            "delivery_date": delivery_date,
            "estimated_value": estimated_value,
            "notes": notes,
            "exam_attended": exam_attended,
            "exam_certified": exam_certified,
        }.items() if v is not None
    }
    
    # Update prospect
    prospect = await prospect_service.update_prospect(
        db, prospect_id, ProspectUpdate(**update_data)
    )
    
    # Handle payment replacement
    if replace_payments and payments_json:
        # Delete existing payments
        await payment_service.delete_payments_by_prospect(db, prospect_id)
        
        # Create new payments
        payment_creates = _parse_inline_payments(payments_json)
        for i, payment_data in enumerate(payment_creates):
            payment_data.prospect_id = prospect_id
            receipt = payment_receipts[i] if i < len(payment_receipts) else None
            if receipt and receipt.filename and receipt.size > 0:
                pass
            else:
                receipt = None
            
            await payment_service.create_payment(
                db, payment_data, current_employee, receipt
            )
    
    await db.refresh(prospect)
    return await prospect_service.get_prospect_out(db, prospect_id)


# ─── Stage Update ────────────────────────────────────────────────

@router.patch("/{prospect_id}/stage", response_model=ProspectOut)
async def update_stage(
    db: DBSession,
    current_employee: CurrentEmployee,
    prospect_id: int,
    stage: str = Form(...),
):
    prospect = await prospect_service.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    prospect.stage = stage
    await db.commit()
    await db.refresh(prospect)
    return await prospect_service.get_prospect_out(db, prospect_id)


# ─── Exam Update ─────────────────────────────────────────────────

@router.patch("/{prospect_id}/exam", response_model=ProspectOut)
async def update_exam(
    db: DBSession,
    current_employee: CurrentEmployee,
    prospect_id: int,
    exam_attended: Optional[bool] = Form(None, alias="examAttended"),
    exam_certified: Optional[bool] = Form(None, alias="examCertified"),
):
    prospect = await prospect_service.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    if exam_attended is not None:
        prospect.exam_attended = exam_attended
    if exam_certified is not None:
        prospect.exam_certified = exam_certified
    
    await db.commit()
    await db.refresh(prospect)
    return await prospect_service.get_prospect_out(db, prospect_id)


# ─── Documents ───────────────────────────────────────────────────

@router.get("/{prospect_id}/documents")
async def get_documents(
    db: DBSession,
    current_user: CurrentAnyUser,
    prospect_id: int,
):
    prospect = await prospect_service.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect.documents


@router.post("/{prospect_id}/documents", status_code=201)
async def upload_document(
    db: DBSession,
    current_employee: CurrentEmployee,
    prospect_id: int,
    doc_type: str = Form(..., alias="docType"),
    file: UploadFile = File(...),
):
    prospect = await prospect_service.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    
    # Delegate to document service
    from app.services import document_service
    document = await document_service.upload_document(
        db, prospect_id, doc_type, file, current_employee
    )
    return document


# ─── Timeline ────────────────────────────────────────────────────

@router.get("/{prospect_id}/timeline")
async def get_timeline(
    db: DBSession,
    current_user: CurrentAnyUser,
    prospect_id: int,
):
    prospect = await prospect_service.get_prospect(db, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect.timeline_events