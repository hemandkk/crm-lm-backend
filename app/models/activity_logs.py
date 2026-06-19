from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base


class ActivityLog(Base):
    """
    Audit trail — login, lead creation, lead updates, stage changes,
    user creation, data exports, password resets, etc.
    No TimestampMixin here on purpose: logs are immutable, so they only
    need created_at (no updated_at).
    """

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_name = Column(String(255), nullable=True)
    user_role = Column(String(20), nullable=True)  # "admin" | "employee" (snapshot at log time)

    action = Column(String(100), nullable=False, index=True)
    # e.g. login, lead_create, lead_update, stage_change, user_create, data_export, password_reset

    entity_type = Column(String(50), nullable=True)   # "prospect" | "user" | etc.
    entity_id = Column(String(50), nullable=True, index=True)

    detail = Column(JSON, nullable=True)  # arbitrary structured context for the action
    ip_address = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
