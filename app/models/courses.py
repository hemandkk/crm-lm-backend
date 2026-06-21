from sqlalchemy import Column, Integer, String, Boolean
from app.database.mixins import TimestampMixin
from app.database import Base
from sqlalchemy.orm import relationship

prospects = relationship(
    "Prospect",
    back_populates="course",
)

class Course(TimestampMixin, Base):
    """Master list of courses — admin-managed dropdown source for prospects."""

    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)