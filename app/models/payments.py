from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Numeric,
    Text,
    DateTime,
    Enum,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class PaymentType(str, enum.Enum):
    advance = "advance"
    installment = "installment"
    final = "final"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)

    prospect_id = Column(
        Integer,
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount = Column(
        Numeric(15, 2),
        nullable=False,
    )

    payment_type = Column(
        Enum(
            PaymentType,
            name="paymenttype",
            create_type=False,
        ),
        nullable=False,
    )

    payment_date = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    receipt_url = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    created_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    prospect = relationship(
        "Prospect",
        back_populates="payments",
    )

    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
    )