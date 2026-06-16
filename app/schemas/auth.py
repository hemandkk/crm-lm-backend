from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    employee_id: str
    password: str

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

class AuthUser(BaseModel):
    id: int
    name: str
    email: str | None = None
    employee_id: str | None = None
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: AuthUser
    role: str