from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
import enum
from sqlalchemy import Enum


class ProspectStage(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"

class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    prospect_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    password: Mapped[str | None] = mapped_column(String(50))

    email: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(String(20))

    father_name: Mapped[str | None] = mapped_column(String(255))
    mother_name: Mapped[str | None] = mapped_column(String(255))

    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id")
    )

    specialization: Mapped[str | None] = mapped_column(String(255))

    address: Mapped[str | None] = mapped_column(Text)

    estimated_deal_value: Mapped[float] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=0,
    )

    delivery_address: Mapped[str | None] = mapped_column(Text)

    delivery_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    notes: Mapped[str | None] = mapped_column(Text)

    # If using PostgreSQL enum
    stage: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        default="new",
    )

    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id")
    )

    exam_attended: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    exam_certified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    sheets_synced: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    sheets_row_id: Mapped[str | None] = mapped_column(
        String(50)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships

    assigned_to = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="prospects",
    )

    course = relationship(
        "Course",
        back_populates="prospects",
    )

    payments = relationship(
        "Payment",
        back_populates="prospect",
        cascade="all, delete-orphan",
    )

    documents = relationship(
        "ProspectDocument",
        back_populates="prospect",
        cascade="all, delete-orphan",
    )

