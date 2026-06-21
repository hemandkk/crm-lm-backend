from sqlalchemy import (Column, ForeignKey, Integer, String, Boolean, DateTime,func, Enum, Numeric)
from app.database.mixins import TimestampMixin
from app.database import Base

import enum
from sqlalchemy.orm import relationship


class UserRole(str, enum.Enum):
    admin = "admin"
    employee = "employee"

class User(TimestampMixin,Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    email = Column(String(255), unique=True, nullable=False, index=True)
    employee_id = Column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=True)
    department = Column(String(50), nullable=True)
    designation = Column(String(50), nullable=True)
    phone = Column(String(12), nullable=True)
    password_hash = Column(String, nullable=False)

    last_login = Column(DateTime(timezone=True))

    last_logout = Column(DateTime(timezone=True))

    role = Column(
        Enum(UserRole),
        nullable=False,
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
    )

    department = Column(String(255))
    designation = Column(String(255))
    phone = Column(String(12))
    joining_date = Column(String(12))
    reporting_manager = Column(String(12))
    salary = Column(String(12))
    address = Column(String(255))
    dob = Column(String(50))
    target = Column(String(12))


