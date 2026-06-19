from app.database.mixins import TimestampMixin
from sqlalchemy import (Column,  Integer, String,ForeignKey, Boolean, DateTime,func, Enum, Numeric)
from app.database.mixins import TimestampMixin
from app.database import Base


class LoginAudit(TimestampMixin, Base):
    __tablename__ = "login_audits"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    login_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    logout_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    ip_address = Column(String(50))

    user_agent = Column(String(500))