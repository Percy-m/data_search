from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class Filter(BaseModel):
    column: str
    operator: str  # 例如: '=', '>', '<', 'in', 'like'
    value: Any

class Metric(BaseModel):
    column: str
    aggregation: str  # 例如: 'sum', 'count', 'avg', 'max', 'min'
    alias: Optional[str] = None

class QueryRequest(BaseModel):
    table: str
    dimensions: List[str] = []
    metrics: List[Metric] = []
    filters: List[Filter] = []
    limit: Optional[int] = 100

class DrillDownRequest(BaseModel):
    base_query: QueryRequest
    drill_down_dimension: str
    current_level_filters: List[Filter]  # 用户点击当前层级时产生的过滤条件

class QueryResult(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]

class RawQueryRequest(BaseModel):
    sql: str
    macros: Optional[Dict[str, str]] = Field(default_factory=dict)

class DrillThroughRequest(BaseModel):
    raw_sql: str
    filters: Dict[str, Any]
    clicked_metric: Optional[str] = None  # 用户点击的具体指标别名/列名
    macros: Optional[Dict[str, str]] = Field(default_factory=dict)
    limit: Optional[int] = 10
    offset: Optional[int] = 0

class DrillThroughResult(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]
    total: int

class DashboardWidgetDTO(BaseModel):
    id: int
    dashboard_id: int
    query_id: int
    x: int
    y: int
    w: int
    h: int
    i: str
    query: Optional[Any] = None # Will hold SavedQuery object

class DashboardAggregateDTO(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: Any
    widgets: List[DashboardWidgetDTO] = []
