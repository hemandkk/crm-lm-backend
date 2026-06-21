from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token

# Database session dependency
DBSession = Annotated[Session, Depends(get_db)]

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        payload = decode_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(401, "Invalid token")

def require_admin(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )
    return current_user


def require_employee(current_user=Depends(get_current_user)):
    return current_user


CurrentAnyUser = Annotated[
    dict,
    Depends(get_current_user),
]

CurrentAdmin = Annotated[
    dict,
    Depends(require_admin),
]

CurrentEmployee = Annotated[
    dict,
    Depends(require_employee),
]