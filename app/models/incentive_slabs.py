from sqlalchemy import Column, Integer, Numeric
from app.database.mixins import TimestampMixin
from app.database import Base


class IncentiveSlab(TimestampMixin, Base):
    """
    Admin-defined incentive brackets, e.g.:
      0      – 100000  -> 5%
      100000 – 200000   -> 5%
      200000 – 300000   -> 6%
      300000 – NULL      -> 8%   (NULL max_amount = unlimited / top bracket)
    """

    __tablename__ = "incentive_slabs"

    id = Column(Integer, primary_key=True)

    min_amount = Column(Numeric(15, 2), nullable=False)
    max_amount = Column(Numeric(15, 2), nullable=True)  # NULL = no upper bound
    rate_percent = Column(Numeric(5, 2), nullable=False)
