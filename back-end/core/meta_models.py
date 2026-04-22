from sqlalchemy import Column, Integer, String, Text, DateTime
from core.database import Base
import datetime

class SavedQuery(Base):
    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    raw_sql = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
