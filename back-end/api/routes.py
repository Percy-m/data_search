from fastapi import APIRouter, HTTPException, Depends
from core.models import QueryRequest, DrillDownRequest, QueryResult, RawQueryRequest, DrillThroughRequest, DrillThroughResult
from core.factory import DataSourceFactory
from services.query import QueryService
import os

# 注册数据源适配器
from adapters.clickhouse import ClickHouseAdapter
DataSourceFactory.register("clickhouse", ClickHouseAdapter)

router = APIRouter()

# 获取数据源服务的依赖注入
def get_query_service() -> QueryService:
    # 实际项目中，这些配置应当从环境变量或配置中心获取
    ds_type = os.getenv("DATA_SOURCE_TYPE", "clickhouse")
    
    try:
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
            raise ValueError(f"Unsupported data source type: {ds_type}")
            
        return QueryService(data_source=adapter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据源初始化失败: {str(e)}")

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
