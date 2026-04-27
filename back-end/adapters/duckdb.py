import duckdb
import sqlglot
from sqlglot import exp
from typing import List, Dict, Any
from core.ports import DataSourcePort
from core.models import QueryRequest, QueryResult, RawQueryRequest, DrillThroughRequest, DrillThroughResult

class DuckDBAdapter(DataSourcePort):
    def __init__(self, database: str, **kwargs):
        # Using database as the file path. If empty, uses in-memory.
        self.db_path = database if database and database.strip() else ':memory:'
        self.conn = duckdb.connect(database=self.db_path)

    def test_connection(self) -> bool:
        try:
            self.conn.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"[DuckDB] Connection test failed: {e}")
            return False

    def execute_query(self, query: QueryRequest) -> QueryResult:
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
                    val = "(" + ",".join([f"'{v}'" if isinstance(v, str) else str(v) for v in f.value]) + ")"
                else:
                    val = str(f.value)
                where_parts.append(f"{f.column} {f.operator} {val}")
            sql += f" WHERE {' AND '.join(where_parts)}"
            
        if query.dimensions:
            sql += f" GROUP BY {', '.join(query.dimensions)}"
            
        if query.order_by:
            sql += f" ORDER BY {query.order_by} {query.order_direction}"
            
        if query.limit:
            sql += f" LIMIT {query.limit}"
            
        try:
            print(f"[DuckDB] Executing SQL: {sql}")
            cursor = self.conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return QueryResult(columns=columns, data=data)
        except Exception as e:
            raise Exception(f"DuckDB query execution failed: {str(e)}")

    def execute_raw_query(self, query: RawQueryRequest) -> QueryResult:
        try:
            ast = sqlglot.parse_one(query.sql, read="duckdb")
            final_sql = ast.sql(dialect="duckdb")
            print(f"[DuckDB] Executing Raw SQL: {final_sql}")
            
            cursor = self.conn.cursor()
            cursor.execute(final_sql)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                columns = []
                data = []
            return QueryResult(columns=columns, data=data)
        except Exception as e:
            print(f"[DuckDB] AST Parse Failed, attempting fallback execution: {e}")
            fallback_sql = query.sql
            cursor = self.conn.cursor()
            cursor.execute(fallback_sql)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                columns = []
                data = []
            return QueryResult(columns=columns, data=data)

    def execute_drill_through(self, request: DrillThroughRequest) -> DrillThroughResult:
        try:
            ast = sqlglot.parse_one(request.raw_sql, read="duckdb")
            
            target_expr = None
            if request.clicked_metric:
                for select in ast.selects:
                    if isinstance(select, exp.Alias) and select.alias == request.clicked_metric:
                        target_expr = select.this
                    elif isinstance(select, exp.Column) and select.name == request.clicked_metric:
                        target_expr = select
                        
            select_projection = "*"
            
            if target_expr:
                if isinstance(target_expr, exp.Count):
                    distinct_node = target_expr.find(exp.Distinct)
                    if distinct_node and distinct_node.expressions:
                        col_expr = distinct_node.expressions[0]
                        if isinstance(col_expr, exp.Column) and col_expr.args.get("table"):
                            table_alias = col_expr.args["table"].sql(dialect="duckdb")
                            select_projection = f"{table_alias}.*"
            
            base_from = ast.find(exp.From)
            if not base_from:
                raise ValueError("Could not extract FROM clause from the provided SQL")
                
            joins = list(ast.find_all(exp.Join))
            where_node = ast.find(exp.Where)
            
            drill_ast = exp.select(select_projection).from_(base_from.this if base_from else "")
            
            for join in joins:
                drill_ast = drill_ast.join(join.this, on=join.args.get("on"), join_type=join.args.get("kind"))
                
            if where_node:
                drill_ast = drill_ast.where(where_node.this)
                
            if request.filters:
                for col_name, col_val in request.filters.items():
                    drill_ast = drill_ast.where(f"{col_name} = '{col_val}'" if isinstance(col_val, str) else f"{col_name} = {col_val}")
                    
            final_sql = drill_ast.sql(dialect="duckdb")
            
            if request.limit:
                final_sql += f" LIMIT {request.limit}"
            if request.offset:
                final_sql += f" OFFSET {request.offset}"
                
            print(f"[DuckDB] Drill Through SQL: {final_sql}")
            
            cursor = self.conn.cursor()
            cursor.execute(final_sql)
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            count_sql = f"SELECT COUNT(*) FROM ({drill_ast.sql(dialect='duckdb')}) as subq"
            cursor.execute(count_sql)
            total = cursor.fetchone()[0]
            
            return DrillThroughResult(columns=columns, data=data, total=total)
            
        except Exception as e:
            print(f"[DuckDB] Drill through execution failed: {e}")
            raise Exception(f"DuckDB drill through execution failed: {str(e)}")

    def get_tables(self) -> List[str]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SHOW TABLES")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[DuckDB] get_tables error: {e}")
            return []

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        try:
            safe_table = table_name.replace("`", "").replace("'", "").replace("\"", "")
            cursor = self.conn.cursor()
            cursor.execute(f"DESCRIBE {safe_table}")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1]
                })
            return columns
        except Exception as e:
            print(f"[DuckDB] get_columns error: {e}")
            return []
