from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database.mixins import TimestampMixin
from app.database import Base

import enum


class DocumentType(str, enum.Enum):
    aadhar = "aadhar"
    photo = "photo"
    sslc = "sslc"
    plus_two = "plus_two"
    degree = "degree"
    agreement = "agreement"


class ProspectDocument(TimestampMixin, Base):
    """One row per uploaded document for a prospect (aadhar, photo, SSLC, etc.)."""

    __tablename__ = "prospect_documents"

    id = Column(Integer, primary_key=True)

    prospect_id = Column(
        Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type = Column(Enum(DocumentType), nullable=False)

    file_url = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=True)

    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    prospect = relationship("Prospect", back_populates="documents")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
