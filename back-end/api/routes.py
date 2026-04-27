from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from core.models import QueryRequest, DrillDownRequest, QueryResult, RawQueryRequest, DrillThroughRequest, DrillThroughResult
from core.factory import DataSourceFactory
from infrastructure.database import get_db
from infrastructure.repositories import SQLAlchemyDataSourceRepository
from core.ports import DataSourceRepositoryPort
from services.query import QueryService
import os

# 注册数据源适配器
from adapters.clickhouse import ClickHouseAdapter
from adapters.duckdb import DuckDBAdapter
DataSourceFactory.register("clickhouse", ClickHouseAdapter)
DataSourceFactory.register("duckdb", DuckDBAdapter)

router = APIRouter()

def get_ds_repository(db: Session = Depends(get_db)) -> DataSourceRepositoryPort:
    return SQLAlchemyDataSourceRepository(db)

# 获取数据源服务的依赖注入，现在支持通过 Header 传递 x-data-source-id
def get_query_service(x_data_source_id: int = Header(None), repo: DataSourceRepositoryPort = Depends(get_ds_repository)) -> QueryService:
    try:
        # 如果前端传递了明确的数据源 ID，则从数据库拉取连接配置
        if x_data_source_id:
            ds_record = repo.get_by_id(x_data_source_id)
            if not ds_record:
                raise ValueError(f"Data source with id {x_data_source_id} not found")
            
            adapter = DataSourceFactory.create(
                ds_record.type,
                host=ds_record.host,
                port=ds_record.port,
                username=ds_record.username,
                password=ds_record.password,
                database=ds_record.database
            )
            ds_id_str = str(x_data_source_id)
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
