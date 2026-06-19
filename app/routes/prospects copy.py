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


class ProspectCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: str = "new"
    course_name: Optional[str] = Field(default=None, alias="courseName")
    notes: Optional[str] = None

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


def _prospect_out(prospect: dict[str, Any]):
    prospect_id = prospect["id"]
    return {
        **prospect,
        "documents": DOCUMENTS.get(prospect_id, []),
        "examAttended": prospect.get("examAttended", False),
        "examCertified": prospect.get("examCertified", False),
    }


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
    prospect.update(updates)
    prospect["updatedAt"] = _now()
    prospect["updated_at"] = prospect["updatedAt"]
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
