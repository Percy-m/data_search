import clickhouse_connect
from core.ports import DataSourcePort
from core.models import QueryRequest, QueryResult, RawQueryRequest

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

    def test_connection(self) -> bool:
        try:
            self.client.ping()
            return True
        except Exception:
            return False
