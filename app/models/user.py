from sqlalchemy import (Column, Integer, String, Boolean, DateTime,func, Enum)
from app.database import Base

import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    employee = "employee"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    email = Column(String(255), unique=True, nullable=False, index=True)
    employee_id = Column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    password_hash = Column(String, nullable=False)


    role = Column(
        Enum(UserRole),
        nullable=False,
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )
