from typing import List, Optional, Any, Dict, Literal
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
    total: int = -1

class RawQueryRequest(BaseModel):
    sql: str
    macros: Optional[Dict[str, str]] = Field(default_factory=dict)
    limit: Optional[int] = None
    offset: Optional[int] = 0

class DrillThroughRequest(BaseModel):
    raw_sql: str
    filters: Dict[str, Any]
    clicked_metric: Optional[str] = None  # 用户点击的具体指标别名/列名
    macros: Optional[Dict[str, str]] = Field(default_factory=dict)
    limit: Optional[int] = None
    offset: Optional[int] = 0
    limit: Optional[int] = 10
    offset: Optional[int] = 0

class DrillThroughResult(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]
    total: int = -1
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

class ComparisonCriterion(BaseModel):
    name: str
    column: str
    mode: Literal["strict_equal", "absolute_tolerance", "percent_tolerance"] = "strict_equal"
    tolerance: Optional[float] = None

class ComparisonConfigPayload(BaseModel):
    name: Optional[str] = None
    data_source_id: Optional[int] = None
    raw_sql: str
    baseline_name: str = "baseline"
    target_name: str = "target"
    baseline_macros: Dict[str, str] = Field(default_factory=dict)
    target_macros: Dict[str, str] = Field(default_factory=dict)
    key_columns: List[str] = Field(default_factory=list)
    group_columns: List[str] = Field(default_factory=list)
    criteria: List[ComparisonCriterion] = Field(default_factory=list)
    compare_columns: List[str] = Field(default_factory=list)
    max_rows: int = 100000

class ComparisonRunRequest(BaseModel):
    comparison_id: Optional[int] = None
    config: Optional[ComparisonConfigPayload] = None
    overrides: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ComparisonDetailRequest(ComparisonRunRequest):
    group_values: Dict[str, Any] = Field(default_factory=dict)
    criterion_name: Optional[str] = None
    status: Literal["match", "mismatch", "baseline_missing", "target_missing"]
    limit: int = 100
    offset: int = 0
