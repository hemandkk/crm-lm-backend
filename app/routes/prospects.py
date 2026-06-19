from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(tags=["Prospects"])

PROSPECTS: dict[str, dict[str, Any]] = {}
DOCUMENTS: dict[str, list[dict[str, Any]]] = {}
PAYMENTS: dict[str, list[dict[str, Any]]] = {}  # prospect_id -> payments
TIMELINE: dict[str, list[dict[str, Any]]] = {}


# ─── Payment Schemas ─────────────────────────────────────────────

class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    payment_type: str = Field(..., alias="paymentType")
    payment_date: str = Field(..., alias="paymentDate")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True

    @field_validator("payment_type")
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        allowed = {"advance", "installment", "final"}
        if v not in allowed:
            raise ValueError(f"paymentType must be one of {allowed}")
        return v


class PaymentCreate(PaymentBase):
    # Used when creating payment inline with prospect
    receipt: Optional[str] = None  # base64 or temp file path


class PaymentOut(PaymentBase):
    id: str
    prospect_id: str = Field(..., alias="prospectId")
    receipt_url: Optional[str] = Field(default=None, alias="receiptUrl")
    created_at: str = Field(..., alias="createdAt")


class PaymentUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    payment_type: Optional[str] = Field(None, alias="paymentType")
    payment_date: Optional[str] = Field(None, alias="paymentDate")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


# ─── Updated Prospect Schemas ────────────────────────────────────

class ProspectCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: str = "new"
    course_name: Optional[str] = Field(default=None, alias="courseName")
    notes: Optional[str] = None
    # New fields matching your frontend form
    father_name: Optional[str] = Field(default=None, alias="fatherName")
    mother_name: Optional[str] = Field(default=None, alias="motherName")
    dob: Optional[str] = None
    course_id: Optional[str] = Field(default=None, alias="courseId")
    specialization: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = Field(default=None, alias="deliveryAddress")
    delivery_date: Optional[str] = Field(default=None, alias="deliveryDate")
    estimated_value: Optional[float] = Field(default=None, alias="estimatedValue")
    # Inline payments for create mode
    payments: list[PaymentCreate] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        extra = "allow"


class ProspectUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: Optional[str] = None
    course_name: Optional[str] = Field(default=None, alias="courseName")
    notes: Optional[str] = None
    father_name: Optional[str] = Field(default=None, alias="fatherName")
    mother_name: Optional[str] = Field(default=None, alias="motherName")
    dob: Optional[str] = None
    course_id: Optional[str] = Field(default=None, alias="courseId")
    specialization: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = Field(default=None, alias="deliveryAddress")
    delivery_date: Optional[str] = Field(default=None, alias="deliveryDate")
    estimated_value: Optional[float] = Field(default=None, alias="estimatedValue")
    exam_attended: Optional[bool] = Field(default=None, alias="examAttended")
    exam_certified: Optional[bool] = Field(default=None, alias="examCertified")
    # Inline payments for edit mode (optional: replace entire array)
    payments: Optional[list[PaymentCreate]] = None

    class Config:
        populate_by_name = True
        extra = "allow"


class StageUpdate(BaseModel):
    stage: str


class ExamUpdate(BaseModel):
    exam_attended: Optional[bool] = Field(default=None, alias="examAttended")
    exam_certified: Optional[bool] = Field(default=None, alias="examCertified")

    class Config:
        populate_by_name = True


# ─── Helpers ─────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc).isoformat()


def _get_prospect(prospect_id: str):
    prospect = PROSPECTS.get(prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return prospect


def _add_timeline(prospect_id: str, event_type: str, description: str):
    event = {
        "id": str(uuid4()),
        "prospectId": prospect_id,
        "prospect_id": prospect_id,
        "type": event_type,
        "description": description,
        "createdAt": _now(),
        "created_at": _now(),
    }
    TIMELINE.setdefault(prospect_id, []).append(event)


def _prospect_out(prospect: dict[str, Any]) -> dict[str, Any]:
    """Enrich prospect with related data."""
    prospect_id = prospect["id"]
    return {
        **prospect,
        "documents": DOCUMENTS.get(prospect_id, []),
        "payments": PAYMENTS.get(prospect_id, []),
        "examAttended": prospect.get("examAttended", False),
        "examCertified": prospect.get("examCertified", False),
    }


def _create_payment(
    prospect_id: str,
    amount: float,
    payment_type: str,
    payment_date: str,
    notes: Optional[str] = None,
    receipt_url: Optional[str] = None,
) -> dict[str, Any]:
    """Create a payment record and return it."""
    payment_id = str(uuid4())
    payment = {
        "id": payment_id,
        "prospectId": prospect_id,
        "prospect_id": prospect_id,
        "amount": amount,
        "paymentType": payment_type,
        "payment_type": payment_type,
        "paymentDate": payment_date,
        "payment_date": payment_date,
        "notes": notes,
        "receiptUrl": receipt_url,
        "receipt_url": receipt_url,
        "createdAt": _now(),
        "created_at": _now(),
    }
    PAYMENTS.setdefault(prospect_id, []).append(payment)
    _add_timeline(
        prospect_id,
        "payment",
        f"Payment of ₹{amount} ({payment_type}) added"
    )
    return payment


# ─── Prospect Endpoints ──────────────────────────────────────────

@router.get("")
def list_prospects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
):
    items = list(PROSPECTS.values())

    if search:
        lowered = search.lower()
        items = [
            item for item in items
            if lowered in item.get("name", "").lower()
            or lowered in item.get("email", "").lower()
            or lowered in item.get("phone", "").lower()
        ]

    if stage:
        items = [item for item in items if item.get("stage") == stage]

    if date_from:
        items = [item for item in items if item.get("createdAt", "") >= date_from]
    if date_to:
        items = [item for item in items if item.get("createdAt", "") <= date_to]

    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start:start + page_size]

    return {
        "data": [_prospect_out(item) for item in page_items],
        "items": [_prospect_out(item) for item in page_items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pageSize": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "totalPages": (total + page_size - 1) // page_size,
    }


@router.post("", status_code=201)
def create_prospect(body: ProspectCreate):
    prospect_id = str(uuid4())
    data = body.model_dump(by_alias=True)
    
    # Extract inline payments before storing
    inline_payments = data.pop("payments", [])
    
    prospect = {
        **data,
        "id": prospect_id,
        "prospect_id": prospect_id,
        "prospectId": prospect_id,
        "createdAt": _now(),
        "created_at": _now(),
        "updatedAt": _now(),
        "updated_at": _now(),
        "examAttended": False,
        "examCertified": False,
    }
    PROSPECTS[prospect_id] = prospect
    
    # Create inline payments if any
    for payment_data in inline_payments:
        _create_payment(
            prospect_id=prospect_id,
            amount=payment_data["amount"],
            payment_type=payment_data["payment_type"],
            payment_date=payment_data["payment_date"],
            notes=payment_data.get("notes"),
            receipt_url=payment_data.get("receipt"),  # temp/base64
        )
    
    _add_timeline(prospect_id, "created", "Prospect created")
    return _prospect_out(prospect)


@router.post("/bulk-import")
async def bulk_import(file: UploadFile = File(...)):
    return {
        "imported": 0,
        "errors": [
            f"Received {file.filename}. Bulk import parsing is not implemented yet."
        ],
    }


@router.get("/{prospect_id}")
def get_prospect(prospect_id: str):
    return _prospect_out(_get_prospect(prospect_id))


@router.put("/{prospect_id}")
def update_prospect(prospect_id: str, body: ProspectUpdate):
    prospect = _get_prospect(prospect_id)
    updates = body.model_dump(exclude_unset=True, by_alias=True)
    
    # Handle inline payments replacement if provided
    inline_payments = updates.pop("payments", None)
    
    prospect.update(updates)
    prospect["updatedAt"] = _now()
    prospect["updated_at"] = prospect["updatedAt"]
    
    # Replace payments if provided in update
    if inline_payments is not None:
        PAYMENTS[prospect_id] = []  # Clear existing
        for payment_data in inline_payments:
            _create_payment(
                prospect_id=prospect_id,
                amount=payment_data["amount"],
                payment_type=payment_data["payment_type"],
                payment_date=payment_data["payment_date"],
                notes=payment_data.get("notes"),
                receipt_url=payment_data.get("receipt"),
            )
    
    _add_timeline(prospect_id, "updated", "Prospect updated")
    return _prospect_out(prospect)


@router.patch("/{prospect_id}/stage")
def update_stage(prospect_id: str, body: StageUpdate):
    prospect = _get_prospect(prospect_id)
    prospect["stage"] = body.stage
    prospect["updatedAt"] = _now()
    prospect["updated_at"] = prospect["updatedAt"]
    _add_timeline(prospect_id, "stage", f"Stage changed to {body.stage}")
    return _prospect_out(prospect)


@router.patch("/{prospect_id}/exam")
def update_exam(prospect_id: str, body: ExamUpdate):
    prospect = _get_prospect(prospect_id)
    if body.exam_attended is not None:
        prospect["examAttended"] = body.exam_attended
        prospect["exam_attended"] = body.exam_attended
    if body.exam_certified is not None:
        prospect["examCertified"] = body.exam_certified
        prospect["exam_certified"] = body.exam_certified
    prospect["updatedAt"] = _now()
    prospect["updated_at"] = prospect["updatedAt"]
    _add_timeline(prospect_id, "exam", "Exam status updated")
    return _prospect_out(prospect)


# ─── Payment Endpoints (Standalone) ──────────────────────────────

@router.get("/{prospect_id}/payments")
def list_payments(prospect_id: str):
    """Get all payments for a prospect."""
    _get_prospect(prospect_id)
    return PAYMENTS.get(prospect_id, [])


@router.post("/{prospect_id}/payments", status_code=201)
async def create_payment(
    prospect_id: str,
    amount: float = Form(..., gt=0),
    payment_type: str = Form(..., alias="paymentType"),
    payment_date: str = Form(..., alias="paymentDate"),
    notes: Optional[str] = Form(None),
    receipt: Optional[UploadFile] = File(None),
):
    """Standalone payment creation (from list page modal)."""
    _get_prospect(prospect_id)
    
    receipt_url = None
    if receipt:
        receipt_url = f"/uploads/receipts/{receipt.filename}"
        # TODO: Actually save the file to disk/storage
    
    payment = _create_payment(
        prospect_id=prospect_id,
        amount=amount,
        payment_type=payment_type,
        payment_date=payment_date,
        notes=notes,
        receipt_url=receipt_url,
    )
    
    return payment


@router.get("/{prospect_id}/payments/{payment_id}")
def get_payment(prospect_id: str, payment_id: str):
    _get_prospect(prospect_id)
    payments = PAYMENTS.get(prospect_id, [])
    for payment in payments:
        if payment["id"] == payment_id:
            return payment
    raise HTTPException(status_code=404, detail="Payment not found")


@router.put("/{prospect_id}/payments/{payment_id}")
async def update_payment(
    prospect_id: str,
    payment_id: str,
    amount: Optional[float] = Form(None),
    payment_type: Optional[str] = Form(None, alias="paymentType"),
    payment_date: Optional[str] = Form(None, alias="paymentDate"),
    notes: Optional[str] = Form(None),
):
    _get_prospect(prospect_id)
    payments = PAYMENTS.get(prospect_id, [])
    
    for payment in payments:
        if payment["id"] == payment_id:
            if amount is not None:
                payment["amount"] = amount
            if payment_type is not None:
                payment["paymentType"] = payment_type
                payment["payment_type"] = payment_type
            if payment_date is not None:
                payment["paymentDate"] = payment_date
                payment["payment_date"] = payment_date
            if notes is not None:
                payment["notes"] = notes
            payment["updatedAt"] = _now()
            payment["updated_at"] = payment["updatedAt"]
            return payment
    
    raise HTTPException(status_code=404, detail="Payment not found")


@router.delete("/{prospect_id}/payments/{payment_id}", status_code=204)
def delete_payment(prospect_id: str, payment_id: str):
    _get_prospect(prospect_id)
    payments = PAYMENTS.get(prospect_id, [])
    PAYMENTS[prospect_id] = [p for p in payments if p["id"] != payment_id]
    return None


# ─── Timeline & Documents ────────────────────────────────────────

@router.get("/{prospect_id}/timeline")
def get_timeline(prospect_id: str):
    _get_prospect(prospect_id)
    return TIMELINE.get(prospect_id, [])


@router.get("/{prospect_id}/documents")
def get_documents(prospect_id: str):
    _get_prospect(prospect_id)
    return DOCUMENTS.get(prospect_id, [])


@router.post("/{prospect_id}/documents", status_code=201)
async def upload_document(
    prospect_id: str,
    doc_type: str = Form(..., alias="docType"),
    file: UploadFile = File(...),
):
    _get_prospect(prospect_id)
    document = {
        "id": str(uuid4()),
        "prospectId": prospect_id,
        "prospect_id": prospect_id,
        "docType": doc_type,
        "doc_type": doc_type,
        "fileName": file.filename,
        "file_name": file.filename,
        "fileUrl": f"/uploads/{file.filename}",
        "file_url": f"/uploads/{file.filename}",
        "createdAt": _now(),
        "created_at": _now(),
    }
    DOCUMENTS.setdefault(prospect_id, []).append(document)
    _add_timeline(prospect_id, "document", f"Uploaded {file.filename}")
    return document