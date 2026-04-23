# 数据可视化报表平台 (Data Visualization BI Platform)

本项目是一个高扩展性、高抽象度的数据查询与可视化报表系统。采用前后端分离架构，前端负责交互与图表渲染，后端负责多数据源的抽象查询与通用下钻计算。

## 1. 架构与设计 (Backend)

后端严格遵循 **端口与适配器模式（六边形架构）**，实现了核心业务逻辑与底层基础设施的彻底解耦。

### 目录结构分层
- **`core/` (核心层)**：定义纯粹的领域模型（如 `QueryRequest`, `DrillDownRequest` 基于 Pydantic）和数据源标准接口（`DataSourcePort`），并引入了由 SQLAlchemy 驱动的元数据模型 (`meta_models.py`) 用以存储数据源配置及看板布局。
- **`adapters/` (适配器层)**：针对具体数据库（如当前实现的 `ClickHouseAdapter`）进行 SQL 翻译和执行。
- **`services/` (服务层)**：封装标准查询和通用下钻算法（`QueryService`）。
- **`api/` (接入层)**：FastAPI 路由和依赖注入控制，支持从 HTTP 请求头中动态加载数据源环境（`x-data-source-id`）。

### 核心设计亮点
- **动态数据源驱动**：告别硬编码的连接配置，系统支持在运行时配置并切换任意数据源（通过元数据库动态加载连接句柄），同时提供了获取表结构 (`get_tables`) 等通用抽象接口。
- **抽象语法树 (AST) 查询**：采用 Pydantic 定义通用的查询请求体（Dimensions, Metrics, Filters），保证业务层无需关心底层数据库。
- **安全的 SQL 解析层**：引入 `sqlglot` 提供 Raw SQL 到 AST 的双向解析能力，保证在进行明细查询（Drill-through）时不会由于前端字符串拼接导致 SQL 注入或语法崩溃。
- **两种多维分析模式**：
  - **Drill-down (聚合下钻)**：作为纯粹的数据结构转换操作（保留指标，替换维度，叠加路径过滤条件），适用于图表层级的层层深挖。
  - **Drill-through (明细穿透)**：允许用户在查看复杂的原生 SQL 聚合指标时，安全地穿透到底层明细表查看原始级数据。后端支持**“智能穿透” (Smart Projection)**，能根据用户点击的不同指标（如 `count(*)` vs `count(DISTINCT customer_id)`）自动切换底层查询投影，返回最匹配意图的细粒度清单或全量宽表。

## 2. 架构与设计 (Frontend)

前端作为数据展示的门户，基于 **Vue 3 (Composition API) + Vite** 构建，采用 **Element Plus** 负责 UI 与表格，结合 **Apache ECharts** 提供高可交互性的可视化图表。

### 核心功能模块 (Dashboard)
页面架构分为三大核心工作区：
1. **配置中心 (Data Sources)**：UI 化的数据源连接池管理。用户可以输入 Host, Port 及账号密码连接 ClickHouse，在保存时系统会主动执行 Ping 测试保证连通性。
2. **数据看板 (Dashboard)**：支持从工作台将调优好的 SQL 一键保存为业务数据看板（存储在独立的元数据库 PostgreSQL 中）。只读视图纯净无干扰，并且支持为看板列**自定义配置条件高亮（染色预警）规则**。
3. **SQL 分析工作台 (Workspace)**：供分析师使用的极客界面。通过切换数据源，左侧会自动渲染出该库底下的**所有表结构（Table Tree）**。点击表名快速填充 SQL，在右侧执行复杂原生 SQL 调试。
4. **可视化数据下钻 (Drill-through)**：三大工作区共享的核心能力，点击结果中的数值指标即可触发基于 AST 解析的智能下钻，穿透至底层明细。

## 3. 快速启动 (Getting Started)

确保您的本地环境已经运行了 ClickHouse（默认监听 `localhost:8123`），并预先配置了本项目的演示数据库 (`bi_demo`)。
数据库中包含了多张模拟业务表用于测试多表 JOIN 和高阶分析：
- `orders` (订单事实表)
- `customers` (客户维度表)
- `shipping` (物流维度表)

> **注:** 关于上述测试表的完整字段字典（Schema）以及适合用来测试复杂“明细穿透”功能的高阶 SQL 示例，请参阅 [table.md](./table.md) 文档。

### 启动元数据数据库 (PostgreSQL)

本项目引入了 PostgreSQL 用于存储用户的固化查询元数据。请使用 Docker 启动服务：

```bash
docker-compose up -d
```
这会在后台启动一个名为 `bi_metadata_db` 的容器，暴露本地 `5432` 端口。

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