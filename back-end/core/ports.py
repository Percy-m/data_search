from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .models import QueryRequest, QueryResult, RawQueryRequest, DrillThroughRequest, DrillThroughResult

class DataSourcePort(ABC):
    """
    数据源抽象接口，所有不同的数据源（ClickHouse, MySQL等）都需要实现此接口
    实现解耦
    """
    @abstractmethod
    def execute_query(self, query: QueryRequest) -> QueryResult:
        pass

    @abstractmethod
    def execute_raw_query(self, query: RawQueryRequest) -> QueryResult:
        pass
        
    @abstractmethod
    def execute_drill_through(self, request: DrillThroughRequest) -> DrillThroughResult:
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        pass
        
    @abstractmethod
    def get_tables(self) -> List[str]:
        """获取当前数据库下所有的表名"""
        pass
        
    @abstractmethod
    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取指定表的所有字段信息 (名称, 类型等)"""
        pass
