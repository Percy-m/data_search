# 数据可视化报表平台 (Data Visualization BI Platform)

本项目是一个高扩展性、高抽象度的数据查询、数据对比与可视化报表系统。采用前后端分离架构，前端负责交互与图表渲染，后端负责多数据源的抽象查询、通用下钻和结果集对比计算。

> **📚 深入了解系统架构**：
> 在经过了三个重大阶段（Phase 1~3）的重构与重塑后，系统已经演变为一个支持无限拖拽画布与智能图表下钻的现代商业级 BI 平台雏形。关于系统演进的核心思路、前后端目录分工职责以及完整的数据流向图，请务必参阅最新的 [**ARCHITECTURE.md 架构文档**](./ARCHITECTURE.md)。
> > 进阶阅读：您可以查看 [**4_plus_1_views.md (4+1架构视图)**](./4_plus_1_views.md)，其中包含了利用 PlantUML 绘制的系统逻辑、开发、进程、场景与部署物理视图。
> 
> **🔧 数据库字典**：
> - 业务测试用表结构 (ClickHouse)：[table.md](./table.md)
> - 系统元数据表结构 (PostgreSQL)：[metadata_schema.md](./metadata_schema.md)
> 
> **🧪 测试规范**：
> - 业务场景梳理与验收测试用例：[TEST_PLAN.md](./TEST_PLAN.md)

> **🧭 SDD 用户侧输入文档**：
> - 产品需求：[PRD.md](./PRD.md)
> - 业务规则：[BUSINESS_RULES.md](./BUSINESS_RULES.md)
> - 路线图：[ROADMAP.md](./ROADMAP.md)
> - 验收标准：[ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md)
> - 领域术语：[DOMAIN_GLOSSARY.md](./DOMAIN_GLOSSARY.md)
> - 数据源说明：[DATA_SOURCE_SPEC.md](./DATA_SOURCE_SPEC.md)
> - 项目约束：[CONSTRAINTS.md](./CONSTRAINTS.md)

## 1. 架构与设计 (Backend)

后端严格遵循 **端口与适配器模式（六边形架构）**，实现了核心业务逻辑与底层基础设施的彻底解耦。

### 目录结构分层
- **`core/` (核心层)**：定义纯粹的领域模型（如 `QueryRequest`, `DrillDownRequest`, `DrillThroughRequest` 基于 Pydantic）和数据源/仓储标准接口（`DataSourcePort`, `MetadataRepository` 等）。
- **`infrastructure/` (基础设施层)**：由 SQLAlchemy 驱动的元数据模型与仓储实现（`orm_models.py`, `repositories.py`），用于存储数据源配置、固化查询和看板布局；表间关联采用逻辑聚合，不依赖物理外键。
- **`adapters/` (适配器层)**：针对具体数据库（当前实现 `ClickHouseAdapter` 与 `DuckDBAdapter`）进行 SQL 翻译、执行以及 `sqlglot` AST 改写。
- **`services/` (服务层)**：封装标准查询、通用下钻、宏变量安全预编译和查询缓存（`QueryService`, `cache.py`）。
- **`api/` (接入层)**：FastAPI 路由和依赖注入控制，支持从 HTTP 请求头中动态加载数据源环境（`x-data-source-id`）。

### 核心设计亮点
- **动态数据源驱动**：告别硬编码的连接配置，系统支持在运行时配置并切换 ClickHouse、DuckDB 等适配器（通过元数据库动态加载连接句柄），同时提供了获取表结构 (`get_tables`) 等通用抽象接口。
- **抽象语法树 (AST) 查询**：采用 Pydantic 定义通用的查询请求体（Dimensions, Metrics, Filters），保证业务层无需关心底层数据库。
- **安全的 SQL 解析层**：引入 `sqlglot` 提供 Raw SQL 到 AST 的双向解析能力，保证在进行明细查询（Drill-through）时不会由于前端字符串拼接导致 SQL 注入或语法崩溃。
- **安全宏变量与缓存**：`QueryService` 在 SQL 进入 AST 解析前完成 `{{macro}}` 字符串级白名单替换，并通过 `cachetools.TTLCache` 对原生查询结果进行单 Worker 内存缓存。
- **独立数据对比**：`ComparisonService` 复用 `QueryService.raw_query()`，支持同一 SQL 在 baseline/target 两组宏变量下的主键对齐、分组汇总、容差比较和明细输出；后端保留单侧 100000 行安全阈值，前端对汇总结果做展示分页。
- **两种多维分析模式**：
  - **Drill-down (聚合下钻)**：作为纯粹的数据结构转换操作（保留指标，替换维度，叠加路径过滤条件），适用于图表层级的层层深挖。
  - **Drill-through (明细穿透)**：允许用户在查看复杂的原生 SQL 聚合指标时，安全地穿透到底层明细表查看原始级数据。后端支持**“智能穿透” (Smart Projection)**，能根据用户点击的不同指标（如 `count(*)` vs `count(DISTINCT customer_id)`）自动切换底层查询投影，返回最匹配意图的细粒度清单或全量宽表。

## 2. 架构与设计 (Frontend)

前端作为数据展示的门户，基于 **Vue 3 (Composition API) + Vite** 构建，采用 **Element Plus** 负责 UI 与表格，结合 **Apache ECharts** 提供高可交互性的可视化图表。

### 核心功能模块 (Dashboard)
页面架构分为四大核心工作区：
1. **配置中心 (Data Sources)**：UI 化的数据源连接池管理。用户可以配置 ClickHouse 的 Host, Port 及账号密码，也可以配置 DuckDB 文件路径；保存时系统会主动执行连接测试保证连通性。
2. **分析工作台 (Queries)**：供分析师使用的极客界面。通过切换数据源，左侧会自动渲染出该库底下的**所有表结构（Table Tree）**。点击表名快速填充 SQL，在右侧执行复杂原生 SQL 调试。不仅支持表格，还支持**一键切换可视化图表类型 (Bar/Line/Pie)**。调试完成后，可将其固化为 **Query 组件**。
3. **数据看板 (Dashboards)**：基于 Vue Grid Layout 与 ECharts 驱动的**无限画布**。用户可以新建看板，并将多个 `Query 组件`（表格或各种图表）添加到画布中自由**拖拽、缩放**和排列组合。每个 Widget 支持独立配置**高亮（染色预警）规则**，表格数据支持分页。
4. **数据对比 (Compare)**：独立工作区，支持配置同一 SQL 的 baseline/target 宏参数、主键列、分组列和对比标准，运行后分页查看汇总、按需打开明细并导出 Excel。
5. **可视化数据下钻 (Drill-through)**：全站共享的核心能力，即使在拖拽组合出的图表组件中，**点击 ECharts 柱体/饼块或表格指标**即可触发基于 AST 解析的智能下钻，穿透至底层明细。

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
