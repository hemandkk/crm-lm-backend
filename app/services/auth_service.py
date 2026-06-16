from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import (
    verify_password,
    create_access_token,
)


def login_user(
    db: Session,
    email: str,
    password: str,
    required_role: str,
):
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        return None

    required_role_value = getattr(required_role, "value", required_role)
    user_role_value = getattr(user.role, "value", user.role)

    if user_role_value != required_role_value:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        password,
        user.password_hash
    ):
        return None

    return create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )



def get_user_by_email(
    db: Session,
    email: str,
):
    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def get_user_by_employee_id(
    db: Session,
    employee_id: str,
):
    return (
        db.query(User)
        .filter(User.employee_id == employee_id)
        .first()
    )

def admin_login(
    db,
    email,
    password,
):
    user = get_user_by_email(
        db,
        email,
    )

    if not user:
        raise HTTPException(
            401,
            "Invalid credentials",
        )

    if user.role != "admin":
        raise HTTPException(
            403,
            "Not an admin",
        )

    if not verify_password(
        password,
        user.password_hash,
    ):
        raise HTTPException(
            401,
            "Invalid credentials",
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }
