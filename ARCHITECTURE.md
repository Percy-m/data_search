# 数据分析控制台架构文档 (Architecture)

## 1. 架构概述 (Overview)

本项目旨在构建一个高扩展性、高抽象度的数据查询与可视化报表后端平台。系统采用**端口与适配器模式（六边形架构）**，实现了核心业务逻辑与底层基础设施（如数据源、Web 框架）的彻底解耦。

在经过了多个阶段的演进后，本项目从最初的单一页面 SQL 工具，升级为一个包含动态数据源连接、组件化拖拽工作台、智能 AST 明细穿透的现代商业级企业 BI 报表引擎。

## 2. 后端架构 (Backend)

后端服务基于 **Python 3.9 + FastAPI** 开发，遵循六边形架构，确保了业务逻辑纯粹且独立。

### 2.1 目录结构与分层

*   **`core/` (核心层)**：系统的核心领域模型和接口定义。不依赖任何外部框架或具体的数据源实现。
    *   `meta_models.py`: SQLAlchemy ORM 模型，负责对接 PostgreSQL 存储引擎系统的全部元数据配置（如数据源连接池、看板画布、图表组件）。
    *   `models.py`: 定义基于 Pydantic 的抽象查询验证模型（`QueryRequest`, `DrillDownRequest`, `DrillThroughRequest` 等）。
    *   `ports.py` & `factory.py`: 数据源抽象标准接口（提供获取表结构、执行查询的规范），以及管理动态实例化的 `DataSourceFactory`。
    *   `database.py`: PostgreSQL Session 连接池配置。
*   **`adapters/` (适配器层)**：具体基础设施的操作层实现。
    *   `clickhouse.py`: ClickHouse 数据源适配器，实现了 `DataSourcePort` 接口，负责将抽象模型翻译为 SQL，直接与原生引擎通信。内部深度集成了 `sqlglot` 用于 AST 语法树智能解析和安全投影改写。
*   **`services/` (服务层)**：业务逻辑层。
    *   `query.py`: `QueryService` 封装了标准的多维查询和通用下钻的算法实现。
*   **`api/` (接入层)**：HTTP 层 (Controllers)。
    *   `dashboards.py`: 大屏/画板的增删改查。
    *   `data_sources.py`: 数据源的动态连接注册与测试。
    *   `saved_queries.py`: 查询图表组件（Widget）的增删改查。
    *   `routes.py`: 核心代理端点，负责根据请求头的环境变量 (`x-data-source-id`) 调用工厂，并将请求分发至相应的 Adapter 服务执行引擎查询或智能下钻。
*   **`main.py`**: 系统入口、中间件装配、元数据库引擎拉起。

### 2.2 核心设计解析

#### 多数据源扩展设计（松耦合）
为了避免数据库绑定困境（如未来需要接入 MySQL、Elasticsearch），后端采用了面向接口编程。
业务行为抽象在 `DataSourcePort` 接口内，针对新 DB 仅需开发对应的 `Adapter`。在运行时，请求路由根据外部入参 `x-data-source-id` 经由 `DataSourceFactory` **动态实例化**并向 `QueryService` 进行依赖注入。业务层完全不感知底层实现，实现了完美解耦。

#### AST 结构化查询与智能穿透设计 (Smart Drill-Through)
传统的 BI 系统在支持基于聚合 SQL（甚至多表 JOIN）查看底层明细时极易由于简单的正则拼接造成语法崩溃。本平台通过引入 `sqlglot` 作为 SQL 解析库，实现了精准的 **Smart Projection（智能投影穿透）**：
1. 后端将前端记录的长文本 SQL 转化为抽象语法树 (AST)。
2. 根据被点击的具体指标类型进行结构变化判断：
   - 比如点击普通 `SUM` 指标：抽离聚合层，直接返回 `SELECT *` 底层宽表供明细对账。
   - 比如点击 `COUNT(DISTINCT table.column)` 去重指标：改写投影为 `SELECT table.* LIMIT 1 BY table.column`，自动过滤出确切的数量，并携带实体自身的上下文供参考，告别了无意义的数据膨胀。
3. 动态且安全地合并保留原始的 `WHERE`/`JOIN` 子句，外加前端点击的维度组合，最终重编译为原生语句并执行。

## 3. 前端架构 (Frontend)

前端作为承载可视化与数据分析的门户，基于 **Vue 3 (Composition API) + Vite** 构建，采用了成熟的高级组件生态来支持极客编辑与图表拖拽。

### 3.1 核心依赖栈
*   **核心引擎**：Vue 3
*   **UI 骨架**：Element Plus
*   **拖拽引擎**：`vue3-grid-layout`（驱动无限画布）
*   **可视化图表**：Apache ECharts + `vue-echarts`

### 3.2 UI 视图模块设计
为了兼顾不同类型用户（分析师、业务阅读方、管理员），前端功能被剥离进三个独立的标签页空间（在 `BiDashboard.vue` 内实现）：

1.  **配置中心 (Data Source Management)**
    *   偏向 DevOps 与管理员角色，用于登记、验证和打通底层的数据库。
2.  **分析工作台 (Query Editor Workspace)**
    *   偏向数据分析师的生产车间。根据选中的数据源，左侧**动态生成业务库的物理表结构树**。主视区是带语法的 SQL 编辑器。查询结果支持预览，并可一键**将表格无缝切换为柱状图、饼图等 ECharts 可视化图表**，最终将其沉淀为一个独立的 “Query 图表组件”。
3.  **数据看板阅览区 (Dashboards Viewer)**
    *   偏向最终业务方的展示层。这块视图纯粹且无代码干扰。基于 `vue-grid-layout` 实现**大屏无限画布**，用户可以将已造好的图表组件拖入，自由调整坐标、大小。
    *   同时，这里也提供了各组件的独立预警阈值入口（**条件格式高亮**），所有呈现在画布上的 ECharts 图表或 Table 均共享全局的 Drill-through（智能穿透）监听交互功能。

### 3.3 交互状态隔离管理
前端充分利用了 Composition API 的特质，在不引入全局 Pinia 的情况下实现了三大 Tab 块之间的**数据物理隔离**。比如在看板区展示的数据结果集合与在 SQL 工作台中调试用的验证集合互相独立，极大增强了修改测试阶段的安全性和无缝连贯的操作体验。