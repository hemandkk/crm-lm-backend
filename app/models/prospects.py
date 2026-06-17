from app.database.mixins import TimestampMixin

class Prospect(TimestampMixin, Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True)

    name = Column(String(255))