from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from core.database import Base
import datetime

class SavedQuery(Base):
    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    raw_sql = Column(Text, nullable=False)
    thresholds = Column(JSON, default=list)  # 新增高亮阈值配置
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
