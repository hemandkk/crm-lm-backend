from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import get_db
from app.models.user import User, UserRole
from app.utils.id_generator import generate_employee_id

router = APIRouter(tags=["Employees"])


class EmployeeCreate(BaseModel):
    email: str
    employee_id: Optional[str] = Field(default=None, alias="employeeId")
    password: str = "Password@123"
    role: UserRole = UserRole.employee
    name: str
    department: str
    designation: str
    phone: str
    status: Literal["active", "inactive"] = "active"

    class Config:
        populate_by_name = True


class EmployeeUpdate(BaseModel):
    email: Optional[str] = None
    employee_id: Optional[str] = Field(default=None, alias="employeeId")
    password: Optional[str] = None
    role: Optional[UserRole] = None
    name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    phone: str
    status: Optional[Literal["active", "inactive"]] = None

    class Config:
        populate_by_name = True


class EmployeeStatusUpdate(BaseModel):
    status: Literal["active", "inactive"]


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(alias="newPassword")

    class Config:
        populate_by_name = True


def _employee_out(user: User):
    status_value = "active" if user.is_active else "inactive"
    return {
        "id": str(user.id),
        "email": user.email,
        "employee_id": user.employee_id,
        "employeeId": user.employee_id,
        "role": user.role.value,
        "name":user.name,
        "status": status_value,
        "is_active": user.is_active,
        "isActive": user.is_active,
    }


def _get_employee(db: Session, employee_id: str) -> User:
    try:
        user_id = int(employee_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return user


@router.get("")
def list_employees(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[Literal["active", "inactive"]] = Query(None, alias="status"),
):
    query = db.query(User)

    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(User.email.ilike(pattern), User.employee_id.ilike(pattern)))

    if status_filter:
        query = query.filter(User.is_active.is_(status_filter == "active"))

    total = query.count()
    users = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "data": [_employee_out(user) for user in users],
        "items": [_employee_out(user) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pageSize": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "totalPages": (total + page_size - 1) // page_size,
    }


@router.post("", status_code=201)
def create_employee(body: EmployeeCreate, db: Session = Depends(get_db)):
    employee_id = body.employee_id

    if not employee_id:
        employee_id = generate_employee_id(db)
    duplicate_filters = [
        User.email == body.email,
        User.employee_id == employee_id
    ]

    """ if body.employee_id:
        duplicate_filters.append(User.employee_id == body.employee_id) """

    existing = db.query(User).filter(or_(*duplicate_filters)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee already exists")

    user = User(
        email=body.email,
        name=body.name,
        employee_id=employee_id,
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=body.status == "active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _employee_out(user)


@router.get("/{employee_id}")
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    return _employee_out(_get_employee(db, employee_id))


@router.put("/{employee_id}")
def update_employee(employee_id: str, body: EmployeeUpdate, db: Session = Depends(get_db)):
    user = _get_employee(db, employee_id)
    data = body.model_dump(exclude_unset=True, by_alias=False)

    if data.get("email") is not None:
        user.email = data["email"]
    if data.get("name") is not None:
        user.name = data["name"]
    if data.get("employee_id") is not None:
        user.employee_id = data["employee_id"]
    if data.get("password") is not None:
        user.password_hash = hash_password(data["password"])
    if data.get("role") is not None:
        user.role = data["role"]
    if data.get("status") is not None:
        user.is_active = data["status"] == "active"

    db.commit()
    db.refresh(user)
    return _employee_out(user)


@router.patch("/{employee_id}/status")
def toggle_status(
    employee_id: str,
    body: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
):
    user = _get_employee(db, employee_id)
    user.is_active = body.status == "active"
    db.commit()
    db.refresh(user)
    return _employee_out(user)


@router.post("/{employee_id}/reset-password")
def reset_password(
    employee_id: str,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    user = _get_employee(db, employee_id)
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password reset successfully"}


@router.get("/{employee_id}/performance")
def get_performance(
    employee_id: str,
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    db: Session = Depends(get_db),
):
    user = _get_employee(db, employee_id)
    return {
        "employeeId": str(user.id),
        "employee_id": str(user.id),
        "dateFrom": date_from,
        "dateTo": date_to,
        "totalProspects": 0,
        "convertedProspects": 0,
        "conversionRate": 0,
        "target": 0,
        "achieved": 0,
    }

@router.get("/meta/next-employee-id")
def get_next_employee_id(db: Session = Depends(get_db)):
    return {
        "employeeId": generate_employee_id(db)
    }
