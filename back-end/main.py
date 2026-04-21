from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as query_router

app = FastAPI(
    title="Data Visualization BI API",
    description="支持抽象数据查询和通用下钻的可视化报表后端",
    version="1.0.0"
)

# 允许跨域请求，方便本地前端调试
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router, prefix="/api/v1/data", tags=["Data Analysis"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
