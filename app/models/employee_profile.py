from sqlalchemy import Column, Integer, String, Boolean
from app.database.mixins import TimestampMixin
from app.database import Base
from sqlalchemy.orm import relationship

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