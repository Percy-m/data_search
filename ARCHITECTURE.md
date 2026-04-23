# 数据分析控制台架构文档 (Architecture)

## 1. 演进路线回顾 (Evolution Roadmap)

本项目最初被设计为一个单一页面的 SQL 演示工具，通过以下三个阶段的密集迭代，现已成功演进为一个初具规模的商业级企业 BI 报表引擎。

### Phase 1: 动态数据源驱动与表结构导航
*   **痛点**：原生架构中，数据库连接配置写死在后端代码与环境变量中，且前端 SQL 编写区完全盲写。
*   **演进**：
    *   引入了独立于业务分析库 (ClickHouse) 的元数据配置库 (PostgreSQL)。
    *   抽象了连接池工厂，实现了在前端录入账号密码、测试连接并在运行时动态按需加载不同数据源的能力。
    *   在工作台加入了 Table Tree，自动拉取数据库表结构，提升分析师编写 SQL 的效率。

### Phase 2: 概念解耦与无限画布组件化
*   **痛点**：以前所有的看板都只是一条条粗糙的保存下来的大段 SQL 代码框。
*   **演进**：
    *   将概念严格拆分为 **分析工作台 (Queries / Widgets)** 与 **数据看板 (Dashboards)**。
    *   前端引入 `vue3-grid-layout`，支持新建无限画布并将任意数量的已存 Query 拖入排版。
    *   实现了各 Widget 在统一画板上的高度自由拖拽、缩放及持久化 Layout 坐标保存，并支持单个卡片的独立“预警高亮规则 (Thresholds)”配置。

### Phase 3: 多元图表化与极简智能穿透
*   **痛点**：大屏只能展现表格（Table），且以前为了支持查询底层明细，前端被动使用极其脆弱的正则拼 SQL，常常引起语法崩溃。
*   **演进**：
    *   深度整合 `Apache ECharts`，工作台支持对 SQL 结果进行柱状图 (Bar)、折线图 (Line)、饼图 (Pie) 的无缝切换与一键存储。
    *   全面接入基于 `sqlglot` 的 AST（抽象语法树）解析中间件。将钻取逻辑沉淀到后端并实现 **Smart Projection (智能投影)**。无论是点击多表复杂的 JOIN 查询、还是针对 `COUNT(DISTINCT)` 触发，都能精准地剥离、合并原查询条件的 `WHERE` 和 `JOIN`，并退化为最小必需集的下钻明细展示，在图表上点击依然纵滑流畅。

---

## 2. 后端架构 (Backend)

后端服务基于 **Python 3.9 + FastAPI** 开发，遵循**端口与适配器（六边形）架构**。

### 2.1 目录职责说明

*   **`main.py`**：应用入口、中间件装配、跨域配置、数据库引擎拉起。
*   **`api/`**：HTTP 层 (Controllers)。
    *   `dashboards.py`：大屏/画板的增删改查。
    *   `data_sources.py`：数据源的连接测试与注册。
    *   `saved_queries.py`：查询组件（Widget）的设计器后台。
    *   `routes.py`：核心业务——代理执行原始 SQL，并负责 AST Drill-through 明细穿透下发。
*   **`core/`**：领域模型与核心基建。
    *   `meta_models.py`：SQLAlchemy ORM 模型，负责对接 PostgreSQL 存储引擎系统的全部元数据配置。
    *   `models.py`：基于 Pydantic 的纯业务对象验证定义。
    *   `ports.py` & `factory.py`：数据库驱动策略层，提供统一规范以随时切入不同 DB。
    *   `database.py`：PostgreSQL Session 工厂连接池。
*   **`adapters/`**：数据操作层实现。
    *   `clickhouse.py`：核心类。通过官方驱动与原生 `clickhouse-client` 通信；且内部深度集成了 `sqlglot` 逻辑用于实现智能下钻时的 SQL AST 解构、组装、`LIMIT 1 BY` 等降级计算规则。

### 2.2 数据流向图 (Data Flow)

当用户在前端画板点击某个 ECharts 饼图请求查看下钻明细时：
1. Request -> `api/routes.py` (携带 ECharts Node 上下文与 Header `x-data-source-id`)。
2. Factory 根据 Header 动态装配生成 `ClickHouseAdapter` 实例对象。
3. `QueryService` 接收到调用，传递给 Adapter 的 `execute_drill_through` 方法。
4. Adapter 使用 `sqlglot` 将该 Widget 保存的原生复杂 SQL 解析为一棵 AST。
5. Adapter 从 AST 中提取底层的 `FROM` 与所有的 `JOIN`。
6. Adapter 动态合并前端传来的点击节点过滤器（如 `country = 'China'`）。
7. Adapter 根据该图表的聚合类型（是普通聚合还是 `COUNT(DISTINCT)`），决定投影模式。
8. 重新编译 AST 树为原生 SQL 字符串交由 ClickHouse 执行，安全返还明细给前台。

---

## 3. 前端架构 (Frontend)

前端基于 **Vue 3 + Vite**，利用了成熟的高级组件生态来构建数据仪表盘。

### 3.1 核心依赖栈
*   **核心引擎**：Vue 3 (Composition API 模式)
*   **UI 骨架**：Element Plus
*   **拖拽引擎**：`vue3-grid-layout`
*   **可视化库**：`echarts` + `vue-echarts`

### 3.2 UI 视图与组件分布
系统为了给不同的用户角色提供最佳体验，主要通过 Tab 拆分为三大独立空间（集中在 `BiDashboard.vue` 内实现状态解耦）：

1.  **配置中心 (Data Source Management)**
    *   偏向 DevOps 角色，用于登记业务库。
2.  **数据看板阅览区 (Dashboards Viewer)**
    *   偏向业务方 (C Level 或运营)。这块视图极度干净，隐藏了所有的代码层。利用 `vue-grid-layout` 展现事先组装好的 `Widget` (以 Table 或 V-Chart 组件挂载)。提供预警高亮过滤入口，同时支持在任意图表或列表上触发深度点击交互探查明细。
3.  **SQL 分析工作台 (Query Editor)**
    *   偏向分析师。左栏调用后端提供的 DB-metadata 接口生成表结构树，主栏为带各种辅助操作（格式化、转图表预览、另存为组件）的大型代码编辑器。

### 3.3 交互状态管理
前端放弃了全局的庞大 Pinia，采用组合式 API (Composition API) 实现单页面应用内不同 Tab 块间状态的安全隔离。
例如：看板阅览区持有的 ECharts 对象及 TableData（即 `boardTableData` / `boardColumns`），与极客工作台中产生的测试数据 (`editorTableData`) 物理隔离，互不干扰，从而支撑了修改、对撞验证后无缝刷新到前台面板的操作连贯性。