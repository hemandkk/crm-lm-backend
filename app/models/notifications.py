from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.mixins import TimestampMixin
from app.database import Base


class Notification(TimestampMixin, Base):
    """
    Notifies an employee — lead assigned, follow-up reminder, stage change, etc.
    """

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    read = Column(Boolean, default=False, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
