from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from core.models import QueryRequest, DrillDownRequest, QueryResult, RawQueryRequest, DrillThroughRequest, DrillThroughResult, ComparisonRunRequest, ComparisonDetailRequest, ComparisonConfigPayload
from core.factory import DataSourceFactory
from infrastructure.database import get_db
from infrastructure.repositories import SQLAlchemyDataSourceRepository, SQLAlchemyComparisonConfigRepository
from core.ports import DataSourceRepositoryPort
from services.query import QueryService
from services.comparison import ComparisonService
import os

# 注册数据源适配器
from adapters.clickhouse import ClickHouseAdapter
from adapters.duckdb import DuckDBAdapter
DataSourceFactory.register("clickhouse", ClickHouseAdapter)
DataSourceFactory.register("duckdb", DuckDBAdapter)

router = APIRouter()

def get_ds_repository(db: Session = Depends(get_db)) -> DataSourceRepositoryPort:
    return SQLAlchemyDataSourceRepository(db)

def create_query_service_for_data_source(data_source_id: int, repo: DataSourceRepositoryPort) -> QueryService:
    ds_record = repo.get_by_id(data_source_id)
    if not ds_record:
        raise ValueError(f"Data source with id {data_source_id} not found")

    adapter = DataSourceFactory.create(
        ds_record.type,
        host=ds_record.host,
        port=ds_record.port,
        username=ds_record.username,
        password=ds_record.password,
        database=ds_record.database
    )
    return QueryService(data_source=adapter, data_source_id=str(data_source_id))

def resolve_comparison_config(request: ComparisonRunRequest, db: Session) -> ComparisonConfigPayload:
    if request.comparison_id:
        repo = SQLAlchemyComparisonConfigRepository(db)
        record = repo.get_by_id(request.comparison_id)
        if not record:
            raise ValueError(f"Comparison config with id {request.comparison_id} not found")
        data = {
            "name": record.name,
            "data_source_id": record.data_source_id,
            "raw_sql": record.raw_sql,
            "baseline_name": record.baseline_name,
            "target_name": record.target_name,
            "baseline_macros": record.baseline_macros or {},
            "target_macros": record.target_macros or {},
            "key_columns": record.key_columns or [],
            "group_columns": record.group_columns or [],
            "criteria": record.criteria or [],
            "compare_columns": record.compare_columns or [],
            "max_rows": record.max_rows or 100000,
        }
        data.update(request.overrides or {})
        return ComparisonConfigPayload(**data)

    if not request.config:
        raise ValueError("请传入 comparison_id 或完整 config")
    data = request.config.dict()
    data.update(request.overrides or {})
    return ComparisonConfigPayload(**data)

# 获取数据源服务的依赖注入，现在支持通过 Header 传递 x-data-source-id
def get_query_service(x_data_source_id: int = Header(None), repo: DataSourceRepositoryPort = Depends(get_ds_repository)) -> QueryService:
    try:
        # 如果前端传递了明确的数据源 ID，则从数据库拉取连接配置
        if x_data_source_id:
            return create_query_service_for_data_source(x_data_source_id, repo)
        else:
            # 兼容旧逻辑/默认本地开发配置
            ds_type = os.getenv("DATA_SOURCE_TYPE", "clickhouse")
            if ds_type == "clickhouse":
                adapter = DataSourceFactory.create(
                    "clickhouse",
                    host=os.getenv("CH_HOST", "localhost"),
                    port=int(os.getenv("CH_PORT", "8123")),
                    username=os.getenv("CH_USER", "default"),
                    password=os.getenv("CH_PASSWORD", ""),
                    database=os.getenv("CH_DB", "default")
                )
            else:
                raise ValueError(f"Unsupported default data source type: {ds_type}")
            ds_id_str = "default"
                
        return QueryService(data_source=adapter, data_source_id=ds_id_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据源初始化失败: {str(e)}")

@router.get("/meta/tables")
def get_tables(service: QueryService = Depends(get_query_service)):
    try:
        tables = service.data_source.get_tables()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/meta/columns/{table_name}")
def get_columns(table_name: str, service: QueryService = Depends(get_query_service)):
    try:
        columns = service.data_source.get_columns(table_name)
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/query", response_model=QueryResult)
def execute_query(request: QueryRequest, service: QueryService = Depends(get_query_service)):
    try:
        return service.query(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/query/raw", response_model=QueryResult)
def execute_raw_query(request: RawQueryRequest, service: QueryService = Depends(get_query_service)):
    try:
        return service.raw_query(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/drill-through", response_model=DrillThroughResult)
def execute_drill_through(request: DrillThroughRequest, service: QueryService = Depends(get_query_service)):
    try:
        return service.drill_through(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/drill-down", response_model=QueryResult)
def execute_drill_down(request: DrillDownRequest, service: QueryService = Depends(get_query_service)):
    try:
        return service.drill_down(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/compare")
def execute_comparison(request: ComparisonRunRequest, db: Session = Depends(get_db), x_data_source_id: int = Header(None)):
    try:
        config = resolve_comparison_config(request, db)
        data_source_id = config.data_source_id or x_data_source_id
        if not data_source_id:
            raise ValueError("请为数据对比配置选择数据源")
        service = create_query_service_for_data_source(data_source_id, SQLAlchemyDataSourceRepository(db))
        return ComparisonService(service).run(config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/compare/detail")
def execute_comparison_detail(request: ComparisonDetailRequest, db: Session = Depends(get_db), x_data_source_id: int = Header(None)):
    try:
        config = resolve_comparison_config(request, db)
        data_source_id = config.data_source_id or x_data_source_id
        if not data_source_id:
            raise ValueError("请为数据对比配置选择数据源")
        service = create_query_service_for_data_source(data_source_id, SQLAlchemyDataSourceRepository(db))
        return ComparisonService(service).detail(
            config=config,
            group_values=request.group_values,
            criterion_name=request.criterion_name,
            status=request.status,
            limit=request.limit,
            offset=request.offset,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
