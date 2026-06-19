from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ─── Payment Schemas ─────────────────────────────────────────────

class PaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    payment_type: str = Field(..., alias="paymentType")
    payment_date: date = Field(..., alias="paymentDate")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class PaymentCreate(PaymentBase):
    prospect_id: int = Field(..., alias="prospectId")
    
    model_config = ConfigDict(populate_by_name=True)


class PaymentOut(BaseModel):
    id: int
    prospect_id: int = Field(..., alias="prospectId")
    amount: float
    payment_type: str = Field(..., alias="paymentType")
    payment_date: Optional[date] = Field(None, alias="paymentDate")
    receipt_url: Optional[str] = Field(None, alias="receiptUrl")
    notes: Optional[str] = None
    created_by: Optional[int] = Field(None, alias="createdBy")
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


# ─── Document Schemas ────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: int
    prospect_id: int = Field(..., alias="prospectId")
    doc_type: str = Field(..., alias="docType")
    file_url: str = Field(..., alias="fileUrl")
    file_name: Optional[str] = Field(None, alias="fileName")
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


# ─── Timeline Schemas ────────────────────────────────────────────

class TimelineEventOut(BaseModel):
    id: int
    prospect_id: int = Field(..., alias="prospectId")
    type: str
    description: str
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


# ─── Prospect Schemas ────────────────────────────────────────────

class ProspectBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: str = "new"
    course_name: Optional[str] = Field(None, alias="courseName")
    course_id: Optional[str] = Field(None, alias="courseId")
    father_name: Optional[str] = Field(None, alias="fatherName")
    mother_name: Optional[str] = Field(None, alias="motherName")
    dob: Optional[str] = None
    specialization: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = Field(None, alias="deliveryAddress")
    delivery_date: Optional[str] = Field(None, alias="deliveryDate")
    estimated_value: Optional[float] = Field(None, alias="estimatedValue")
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ProspectCreate(ProspectBase):
    pass


class ProspectUpdate(ProspectBase):
    name: Optional[str] = None
    stage: Optional[str] = None
    exam_attended: Optional[bool] = Field(None, alias="examAttended")
    exam_certified: Optional[bool] = Field(None, alias="examCertified")

    model_config = ConfigDict(populate_by_name=True)


class ProspectOut(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: str
    course_name: Optional[str] = Field(None, alias="courseName")
    course_id: Optional[str] = Field(None, alias="courseId")
    father_name: Optional[str] = Field(None, alias="fatherName")
    mother_name: Optional[str] = Field(None, alias="motherName")
    dob: Optional[str] = None
    specialization: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = Field(None, alias="deliveryAddress")
    delivery_date: Optional[str] = Field(None, alias="deliveryDate")
    estimated_value: Optional[float] = Field(None, alias="estimatedValue")
    notes: Optional[str] = None
    exam_attended: bool = Field(False, alias="examAttended")
    exam_certified: bool = Field(False, alias="examCertified")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    
    # Relations
    payments: List[PaymentOut] = []
    documents: List[DocumentOut] = []
    timeline_events: List[TimelineEventOut] = []
    
    # Computed
    total_paid: float = 0
    balance: float = 0
    payment_status: str = "Not Paid"
    payment_percentage: int = 0

    model_config = ConfigDict(populate_by_name=True)


# ─── Pagination ──────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    data: List[Any]
    items: List[Any]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    total_pages: int = Field(..., alias="totalPages")

    model_config = ConfigDict(populate_by_name=True)