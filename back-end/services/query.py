import re
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

    def _pre_compile_macros(self, sql: str, macros: dict) -> str:
        """
        [安全预编译]
        在将 SQL 送入数据库或 AST 解析器之前，基于正则替换占位符 {{var}}。
        为防范 SQL 注入，此方法必须限制 macro values 的字符集（例如只允许字母、数字、下划线、短划线）。
        """
        if not macros:
            return sql
            
        compiled_sql = sql
        for k, v in macros.items():
            # 安全校验：宏变量的值只能包含常规字符，严禁包含单双引号、分号等可能破坏 SQL 结构的危险字符
            str_v = str(v)
            if not re.match(r"^[a-zA-Z0-9_\-\.\u4e00-\u9fa5]+$", str_v):
                raise ValueError(f"Macro value for '{k}' contains invalid characters. Only alphanumerics, underscores, hyphens, and dots are allowed for security reasons.")
                
            macro_pattern = f"{{{{{k}}}}}"
            compiled_sql = compiled_sql.replace(macro_pattern, str_v)
            
        return compiled_sql

    def query(self, request: QueryRequest) -> QueryResult:
        """
        执行标准的多维数据查询
        """
        return self.data_source.execute_query(request)

    def raw_query(self, request: RawQueryRequest) -> QueryResult:
        """
        执行原生多表/复杂SQL查询，带有预编译宏替换与 LRU 内存缓存支持
        """
        # Pre-compile SQL securely before any cache hash generation or DB execution
        safe_sql = self._pre_compile_macros(request.sql, request.macros)
        
        cache_key = generate_cache_key(self.data_source_id, safe_sql, {"limit": request.limit, "offset": request.offset}) # macros are already compiled into SQL
        
        cached_res = get_cached_result(cache_key)
        if cached_res is not None:
            print(f"[Cache] HIT for query fingerprint: {cache_key[:8]}")
            return cached_res
            
        print(f"[Cache] MISS for query fingerprint: {cache_key[:8]}, querying database...")
        
        # Override the request's SQL with our compiled safe version
        request.sql = safe_sql
        result = self.data_source.execute_raw_query(request)
        
        # 写入缓存
        set_cached_result(cache_key, result)
        return result

    def drill_through(self, request: DrillThroughRequest) -> DrillThroughResult:
        """
        查看底层明细数据 (Drill-through)
        利用后端AST安全解析SQL，避免前端正则暴露
        """
        # Pre-compile SQL securely
        safe_sql = self._pre_compile_macros(request.raw_sql, request.macros)
        request.raw_sql = safe_sql
        
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
