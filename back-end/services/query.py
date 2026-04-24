from core.models import QueryRequest, DrillDownRequest, QueryResult, RawQueryRequest, DrillThroughRequest, DrillThroughResult
from core.ports import DataSourcePort
from core.cache import generate_cache_key, get_cached_result, set_cached_result

class QueryService:
    """
    通用查询与数据下钻服务
    不依赖于具体的数据源实现，也不依赖于具体的数据表字段
    """
    def __init__(self, data_source: DataSourcePort, data_source_id: str = "default"):
        self.data_source = data_source
        self.data_source_id = data_source_id

    def query(self, request: QueryRequest) -> QueryResult:
        """
        执行标准的多维数据查询
        """
        return self.data_source.execute_query(request)

    def raw_query(self, request: RawQueryRequest) -> QueryResult:
        """
        执行原生多表/复杂SQL查询，并带有 LRU 级内存缓存支持
        """
        cache_key = generate_cache_key(self.data_source_id, request.sql, request.macros)
        
        cached_res = get_cached_result(cache_key)
        if cached_res is not None:
            print(f"[Cache] HIT for query fingerprint: {cache_key[:8]}")
            return cached_res
            
        print(f"[Cache] MISS for query fingerprint: {cache_key[:8]}, querying database...")
        # 实际查询底层数据源
        result = self.data_source.execute_raw_query(request)
        
        # 写入缓存
        set_cached_result(cache_key, result)
        return result

    def drill_through(self, request: DrillThroughRequest) -> DrillThroughResult:
        """
        查看底层明细数据 (Drill-through)
        利用后端AST安全解析SQL，避免前端正则暴露
        """
        return self.data_source.execute_drill_through(request)

    def drill_down(self, request: DrillDownRequest) -> QueryResult:
        """
        执行数据下钻
        """
        new_query = QueryRequest(
            table=request.base_query.table,
            dimensions=[request.drill_down_dimension],
            metrics=request.base_query.metrics,
            filters=request.base_query.filters + request.current_level_filters,
            limit=request.base_query.limit
        )
        return self.data_source.execute_query(new_query)
