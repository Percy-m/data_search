# 数据可视化报表平台 (Data Visualization BI Platform)

本项目是一个高扩展性、高抽象度的数据查询与可视化报表系统。采用前后端分离架构，前端负责交互与图表渲染，后端负责多数据源的抽象查询与通用下钻计算。

## 1. 架构与设计 (Backend)

后端严格遵循 **端口与适配器模式（六边形架构）**，实现了核心业务逻辑与底层基础设施的彻底解耦。

### 目录结构分层
- **`core/` (核心层)**：定义纯粹的领域模型（如 `QueryRequest`, `DrillDownRequest` 基于 Pydantic）和数据源标准接口（`DataSourcePort`）。
- **`adapters/` (适配器层)**：针对具体数据库（如当前实现的 `ClickHouseAdapter`）进行 SQL 翻译和执行。
- **`services/` (服务层)**：封装标准查询和通用下钻算法（`QueryService`）。
- **`api/` (接入层)**：FastAPI 路由和依赖注入控制。

### 核心设计亮点
- **抽象语法树 (AST) 查询**：采用 Pydantic 定义通用的查询请求体（Dimensions, Metrics, Filters），保证业务层无需关心底层数据库。
- **安全的 SQL 解析层**：引入 `sqlglot` 提供 Raw SQL 到 AST 的双向解析能力，保证在进行明细查询（Drill-through）时不会由于前端字符串拼接导致 SQL 注入或语法崩溃。
- **两种多维分析模式**：
  - **Drill-down (聚合下钻)**：作为纯粹的数据结构转换操作（保留指标，替换维度，叠加路径过滤条件），适用于图表层级的层层深挖。
  - **Drill-through (明细穿透)**：允许用户在查看复杂的原生 SQL 聚合指标时，安全地穿透到底层明细表查看原始级数据。

## 2. 架构与设计 (Frontend)

前端作为数据展示的门户，基于 **Vue 3 (Composition API) + Vite** 构建，采用 **Element Plus** 负责 UI 与表格，结合 **Apache ECharts** 提供高可交互性的可视化图表。

### 核心功能模块 (Dashboard)
页面包含三个主要功能 Tab：
1. **基础明细查询**：可视化配置表名与维度字段，获取表格格式的二维结果数据。
2. **自定义 SQL 分析**：直接向底层数据源发送复杂的原生 SQL 语句（如包含多表 JOIN、子查询等），用于高阶分析。
3. **可视化数据下钻**：
   - 配置特定的下钻路径（如 `country -> city -> category`）。
   - 图表结合 ECharts `click` 事件。
   - 点击特定柱体（如“中国”）时，前端自动拼装上下文过滤条件并调用下钻接口，实现图表的动态刷新和层级深挖。支持面包屑导航和上钻回退。

## 3. 快速启动 (Getting Started)

确保您的本地环境已经运行了 ClickHouse（默认监听 `localhost:8123`），并预先配置了本项目的演示数据库 (`bi_demo`)。
数据库中包含了多张模拟业务表用于测试多表 JOIN 和高阶分析：
- `orders` (订单事实表)
- `customers` (客户维度表)
- `shipping` (物流维度表)

### 启动后端 (FastAPI)

后端自带隔离的虚拟环境 `.venv`。

```bash
cd back-end
# 启动 FastAPI 服务 (默认运行在 8000 端口)
.venv/bin/python -m uvicorn main:app --reload
```
后端 API 文档 (Swagger UI) 可以在启动后访问：http://127.0.0.1:8000/docs

### 启动前端 (Vue 3)

需要本地有 Node.js 环境。

```bash
cd front-end
# 安装依赖 (首次运行时)
npm install

# 启动 Vite 开发服务器 (默认运行在 5173 端口)
npm run dev
```

启动完成后，打开浏览器访问控制台提示的地址（通常是 http://localhost:5173/），即可体验完整的数据可视化与下钻功能！