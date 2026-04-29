import clickhouse_connect
import sqlglot
from sqlglot import exp
import re
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
        total_count = -1
        try:
            ast = sqlglot.parse_one(query.sql, read="clickhouse")
            base_sql = ast.sql(dialect="clickhouse")
            final_sql = base_sql
            
            if query.limit is not None:
                try:
                    count_sql = f"SELECT count(*) FROM ({base_sql}) AS __subq"
                    count_result = self.client.query(count_sql)
                    total_count = int(count_result.result_rows[0][0])
                    final_sql = f"{base_sql} LIMIT {query.limit} OFFSET {query.offset}"
                except Exception as ce:
                    print(f"[ClickHouse] Count failed: {ce}")
            
            print(f"[ClickHouse] Executing Raw SQL: {final_sql}")
            result = self.client.query(final_sql)
            columns = result.column_names
            data = [dict(zip(columns, row)) for row in result.result_rows]
            return QueryResult(columns=columns, data=data, total=total_count)
            
        except Exception as e:
            print(f"[ClickHouse] AST Parse Failed, attempting fallback execution: {e}")
            fallback_sql = query.sql
            if query.limit is not None:
                try:
                    count_sql = f"SELECT count(*) FROM ({fallback_sql}) AS __subq"
                    count_result = self.client.query(count_sql)
                    total_count = int(count_result.result_rows[0][0])
                    fallback_sql = f"{fallback_sql} LIMIT {query.limit} OFFSET {query.offset}"
                except Exception as ce:
                    print(f"[ClickHouse] Fallback count failed: {ce}")
                    
            result = self.client.query(fallback_sql)
            columns = result.column_names
            data = [dict(zip(columns, row)) for row in result.result_rows]
            return QueryResult(columns=columns, data=data, total=total_count)

    def execute_drill_through(self, request: DrillThroughRequest) -> DrillThroughResult:
        try:
            # At this point, request.raw_sql is already macro-free thanks to the Service layer pre-compilation
            ast = sqlglot.parse_one(request.raw_sql, read="clickhouse")
            
            # Find the targeted metric if specified
            target_expr = None
            if request.clicked_metric:
                for select in ast.selects:
                    if isinstance(select, exp.Alias) and select.alias == request.clicked_metric:
                        target_expr = select.this
                    elif isinstance(select, exp.Column) and select.name == request.clicked_metric:
                        target_expr = select
                        
            # Determine SELECT projection based on the metric clicked
            select_projection = "*"
            limit_by_expr = None
            
            if target_expr:
                if isinstance(target_expr, exp.Count):
                    # For COUNT(DISTINCT table.col), we want to project table.* to show all related info of that entity
                    # and use LIMIT 1 BY col to ensure we only get exactly as many rows as the distinct count.
                    distinct_node = target_expr.find(exp.Distinct)
                    if distinct_node and distinct_node.expressions:
                        col_expr = distinct_node.expressions[0]
                        limit_by_expr = col_expr
                        
                        if isinstance(col_expr, exp.Column) and col_expr.args.get("table"):
                            table_alias = col_expr.args["table"].sql(dialect="clickhouse")
                            select_projection = f"{table_alias}.*"
                        else:
                            select_projection = f"{col_expr.sql(dialect='clickhouse')}"
                elif isinstance(target_expr, (exp.Sum, exp.Avg, exp.Max, exp.Min)):
                    # For sum/avg/max/min, it's often useful to just show the underlying detail records for that column and related context
                    select_projection = "*"

            # Create a new query extracting just the FROM and WHERE from original AST
            from_node = ast.find(exp.From)
            if not from_node:
                raise ValueError("Could not extract FROM clause from the provided SQL")
                
            new_ast = sqlglot.parse_one(f"SELECT {select_projection} FROM {from_node.this.sql(dialect='clickhouse')}", read="clickhouse")
            
            # Carry over original JOINs if any
            joins = list(ast.find_all(exp.Join))
            if joins:
                new_ast.set("joins", joins)
            
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

            # Apply LIMIT BY if we are doing smart distinct entity projection
            if limit_by_expr:
                new_ast = new_ast.limit(1)
                new_ast.args['limit'].set('expressions', [limit_by_expr])

            # Generate base SQL for counting before limits are applied
            base_sql = new_ast.sql(dialect="clickhouse")
            
            # For count queries, we must count the subquery to get total rows
            count_sql = f"SELECT COUNT(*) AS total FROM ({base_sql})"
            print(f"[ClickHouse] Executing Drill-through Count SQL: {count_sql}")
            count_result = self.client.query(count_sql)
            total = count_result.result_rows[0][0] if count_result.result_rows else 0

            # Add regular pagination limits
            # Note: sqlglot might overwrite the limit value if we just call .limit() again, 
            # but we actually want the global limit, which in ClickHouse is placed at the very end
            # Using sqlglot to append regular limits on top of a query that might already have LIMIT BY
            # can be tricky with AST modification, so we'll construct the final query string directly.
            
            data_sql = base_sql
            if request.limit is not None:
                data_sql += f" LIMIT {request.limit}"
            if request.offset is not None:
                data_sql += f" OFFSET {request.offset}"
                
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

    def get_tables(self) -> list:
        try:
            result = self.client.query("SHOW TABLES")
            return [row[0] for row in result.result_rows]
        except Exception as e:
            print(f"[ClickHouse] get_tables error: {e}")
            return []

    def get_columns(self, table_name: str) -> list:
        try:
            # Prevent simple injection since table_name isn't easily parameterized in all drivers
            safe_table = table_name.replace("`", "").replace("'", "").replace("\"", "")
            result = self.client.query(f"DESCRIBE TABLE {safe_table}")
            # ClickHouse DESCRIBE returns: name, type, default_type, default_expression, comment, codec_expression, ttl_expression
            columns = []
            for row in result.result_rows:
                columns.append({
                    "name": row[0],
                    "type": row[1]
                })
            return columns
        except Exception as e:
            print(f"[ClickHouse] get_columns error: {e}")
            return []
