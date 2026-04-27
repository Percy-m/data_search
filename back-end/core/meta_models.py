from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
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
    password = Column(String(255), nullable=True)
    database = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SavedQuery(Base):
    """
    保存的查询，即一个可复用的数据组件 (Widget Base)
    """
    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True) # 关联数据源
    raw_sql = Column(Text, nullable=False)
    macros = Column(JSON, default=list)  # 查询参数(如 {{version}} 等)配置
    thresholds = Column(JSON, default=list)  # 高亮阈值配置
    chart_type = Column(String(50), default="table") # 图表类型: table, bar, pie, line
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Dashboard(Base):
    """
    数据看板画布
    """
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")

class DashboardWidget(Base):
    """
    看板上的具体小组件实例及布局信息
    """
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey('dashboards.id'), nullable=False)
    query_id = Column(Integer, ForeignKey('saved_queries.id'), nullable=False)
    
    # 布局参数 (Vue Grid Layout)
    x = Column(Integer, default=0)
    y = Column(Integer, default=0)
    w = Column(Integer, default=12)
    h = Column(Integer, default=8)
    i = Column(String(50), nullable=False) # 唯一标识符，对于 vue-grid-layout 必需
    
    dashboard = relationship("Dashboard", back_populates="widgets")
    query = relationship("SavedQuery")
