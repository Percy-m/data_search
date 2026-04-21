import clickhouse_connect
import sqlglot
from sqlglot import exp
from core.ports import DataSourcePort
from core.models import QueryRequest, QueryResult, RawQueryRequest, DrillThroughRequest, DrillThroughResult

class ClickHouseAdapter(DataSourcePort):
    def __init__(self, host: str, port: int, username: str, password: str, database: str):
        self.client = clickhouse_connect.get_client(
            host=host, port=port, username=username, password=password, database=database
        )

    def _build_sql(self, query: QueryRequest) -> str:
        select_parts = []
        for dim in query.dimensions:
            select_parts.append(dim)
        for metric in query.metrics:
            alias_part = f" AS {metric.alias}" if metric.alias else ""
            select_parts.append(f"{metric.aggregation.upper()}({metric.column}){alias_part}")
            
        select_clause = ", ".join(select_parts) if select_parts else "*"
        sql = f"SELECT {select_clause} FROM {query.table}"
        
        if query.filters:
            where_parts = []
            for f in query.filters:
                if isinstance(f.value, str):
                    val = f"'{f.value}'"
                elif isinstance(f.value, list):
                    val = tuple(f.value) if len(f.value) > 1 else f"('{f.value[0]}')"
                else:
                    val = f.value
                where_parts.append(f"{f.column} {f.operator} {val}")
            sql += " WHERE " + " AND ".join(where_parts)
            
        if query.dimensions and query.metrics:
            sql += " GROUP BY " + ", ".join(query.dimensions)
            
        if query.limit:
            sql += f" LIMIT {query.limit}"
            
        return sql

    def execute_query(self, query: QueryRequest) -> QueryResult:
        sql = self._build_sql(query)
        print(f"[ClickHouse] Executing SQL: {sql}")
        result = self.client.query(sql)
        columns = result.column_names
        data = [dict(zip(columns, row)) for row in result.result_rows]
        return QueryResult(columns=columns, data=data)

    def execute_raw_query(self, query: RawQueryRequest) -> QueryResult:
        print(f"[ClickHouse] Executing Raw SQL: {query.sql}")
        result = self.client.query(query.sql)
        columns = result.column_names
        data = [dict(zip(columns, row)) for row in result.result_rows]
        return QueryResult(columns=columns, data=data)

    def execute_drill_through(self, request: DrillThroughRequest) -> DrillThroughResult:
        try:
            # Parse original SQL safely using sqlglot
            ast = sqlglot.parse_one(request.raw_sql, read="clickhouse")
            
            # Create a new query extracting just the FROM and WHERE from original AST
            from_node = ast.find(exp.From)
            if not from_node:
                raise ValueError("Could not extract FROM clause from the provided SQL")
                
            new_ast = exp.select("*").from_(from_node.this)
            
            # Carry over original WHERE conditions if any
            where_node = ast.find(exp.Where)
            if where_node:
                new_ast = new_ast.where(where_node.this)
            
            # Add drill-down specific filters
            for k, v in request.filters.items():
                if isinstance(v, str):
                    new_ast = new_ast.where(f"{k} = '{v}'")  # Simple handling, parameterization is safer but we construct sql here
                elif v is not None:
                    new_ast = new_ast.where(f"{k} = {v}")

            # Generate base SQL for counting before limits are applied
            base_sql = new_ast.sql(dialect="clickhouse")
            count_sql = f"SELECT COUNT(*) AS total FROM ({base_sql})"
            print(f"[ClickHouse] Executing Drill-through Count SQL: {count_sql}")
            count_result = self.client.query(count_sql)
            total = count_result.result_rows[0][0] if count_result.result_rows else 0

            # Add limits for paginated actual data query
            if request.limit is not None:
                new_ast = new_ast.limit(request.limit)
            if request.offset is not None:
                new_ast = new_ast.offset(request.offset)
                
            data_sql = new_ast.sql(dialect="clickhouse")
            print(f"[ClickHouse] Executing Drill-through Data SQL: {data_sql}")
            
            data_result = self.client.query(data_sql)
            columns = data_result.column_names
            data = [dict(zip(columns, row)) for row in data_result.result_rows]
            
            return DrillThroughResult(columns=columns, data=data, total=total)

        except Exception as e:
            raise Exception(f"Failed to generate/execute drill-through query: {e}")

    def test_connection(self) -> bool:
        try:
            self.client.ping()
            return True
        except Exception:
            return False
