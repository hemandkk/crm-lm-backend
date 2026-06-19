from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class RefreshToken(Base):
    """
    Hashed refresh tokens for JWT + Refresh Token auth flow.
    Never store the raw token — only its SHA-256 hash.
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(255), unique=True, nullable=False, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
