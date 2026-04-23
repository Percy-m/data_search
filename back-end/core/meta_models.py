from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from core.database import Base
import datetime

class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), nullable=False)  # e.g., clickhouse, mysql
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True) # In a real system, this should be encrypted
    database = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SavedQuery(Base):
    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    # Future scaling: data_source_id = Column(Integer, ForeignKey('data_sources.id'))
    raw_sql = Column(Text, nullable=False)
    thresholds = Column(JSON, default=list)  # 新增高亮阈值配置
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
