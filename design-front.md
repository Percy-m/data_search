# 数据可视化报表平台前端设计方案

## 1. 目标与需求分析
前端作为承载可视化与数据分析的门户，需要支持以下三大核心能力：
1. **普通的数据查询**：可视化查看表内原始数据或简单聚合数据。
2. **多表负载SQL查询**：支持用户直接输入自定义的复杂SQL（包含多表JOIN、子查询等），由前端发送至后端执行并展示结果。
3. **支持聚合查询与数据下钻**：图形化展示数据（如柱状图、饼图等），支持点击图表元素（如特定柱子）自动触发下钻操作，展示下一层级维度的数据。

## 2. 前端技术选型
- **核心框架**：Vue 3 (Composition API) + Vite 构建
- **UI组件库**：Element Plus（用于布局、表单、表格和基础组件）
- **可视化图表**：Apache ECharts（提供强大的交互式图表，完美支持下钻所需的点击事件监听）
- **HTTP请求**：Axios

## 3. 前端架构与模块设计
整个前端页面被设计为包含三个主要Tab页面的单页面应用（Dashboard）：
1. **基础明细查询 (Tab 1)**：
   - 提供表名输入和简单的行列配置。
   - 展示查询出的二维表格数据。
2. **自定义SQL分析 (Tab 2)**：
   - 提供一个文本输入域供用户输入复杂的SQL语句（如 `SELECT t1.id, t2.name FROM t1 JOIN t2 ON ...`）。
   - 展示执行后的表格结果。
3. **可视化数据下钻 (Tab 3)**：
   - 设定一条下钻路径（例如：`country -> city`）。
   - 初始化时查询顶层维度（如`country`）的指标数据并渲染为柱状图。
   - 绑定ECharts的 `click` 事件。当用户点击某个柱子时，记录过滤条件（如 `country='中国'`），调用后端的 `/drill-down` 接口获取下一层维度（`city`）的数据并重绘图表。
   - 提供一个“返回上级”的按钮，用于回退状态，实现上钻。

## 4. 后端接口支持与改造方案
为了支撑前端的“多表负载SQL查询”需求，后端需要拓展支持“原生SQL”执行能力。
**后端需新增的设计**：
1. **模型层 (`core/models.py`)**：新增 `RawQueryRequest` 模型，只包含 `sql: str`。
2. **端口层 (`core/ports.py`)**：在 `DataSourcePort` 接口中增加 `execute_raw_query(self, query: RawQueryRequest)` 方法。
3. **适配器层 (`adapters/clickhouse.py`)**：实现 `execute_raw_query` 方法，直接将SQL发给引擎并返回标准化结果。
4. **服务层 (`services/query.py`)**：新增 `raw_query` 透传方法。
5. **API层 (`api/routes.py`)**：新增 `POST /api/v1/data/query/raw` 路由端点。

前后端接口联调将包括三个核心Endpoint：
- `/api/v1/data/query` : 标准查询
- `/api/v1/data/drill-down` : 状态下钻
- `/api/v1/data/query/raw` : 自定义复杂查询