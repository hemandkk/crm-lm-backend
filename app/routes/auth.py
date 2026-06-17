from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.database.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import login_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class EmployeeLoginRequest(BaseModel):
    employee_id: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(alias="refreshToken")

    class Config:
        populate_by_name = True


def _auth_response(user: User, access_token: str):
    refresh_token = create_refresh_token({"sub": str(user.id), "role": user.role.value})
    return {
        "access_token": access_token,
        "accessToken": access_token,
        "refresh_token": refresh_token,
        "refreshToken": refresh_token,
        "token_type": "bearer",
        "tokenType": "bearer",
        "role": user.role.value,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "employee_id": user.employee_id,
            "employeeId": user.employee_id,
            "name":user.name,
            "role": user.role.value,
            "status": "active" if user.is_active else "inactive",
        },
    }


@router.post("/admin/login")
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    token = login_user(db, payload.email, payload.password, UserRole.admin)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    user = UserRepository.get_by_email(db, payload.email)
    return _auth_response(user, token)


@router.post("/employee/login")
def employee_login(payload: EmployeeLoginRequest, db: Session = Depends(get_db)):
    user = UserRepository.get_by_employee_id(db, payload.employee_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee credentials",
        )

    token = login_user(db, user.email, payload.password, UserRole.employee)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid employee credentials",
        )

    return _auth_response(user, token)


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        claims = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = UserRepository.get_by_id(db, int(claims["sub"]))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return _auth_response(user, access_token)


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}
""" .\.venv\Scripts\python.exe -c "from app.database.session import SessionLocal; from app.models.user import User, UserRole; from app.core.security import hash_password; db=SessionLocal(); email='admin@example.com'; password='Admin@123'; existing=db.query(User).filter(User.email==email).first(); print('Admin already exists' if existing else 'Creating admin'); db.add(User(email=email, employee_id=None, password_hash=hash_password(password), role=UserRole.admin, is_active=True)) if not existing else None; db.commit(); db.close()"
 """