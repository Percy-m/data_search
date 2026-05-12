# 领域术语表 (Domain Glossary)

本文档记录项目内统一使用的业务和技术术语。新增需求中出现新名词时，应先补充到本文档。

| 术语 | 英文 / 代码名 | 定义 |
| :--- | :--- | :--- |
| 数据源 | Data Source | 可被平台连接并查询的业务数据库，如 ClickHouse、DuckDB |
| 元数据库 | Metadata Database | 平台自身用于保存配置的 PostgreSQL 数据库 |
| 业务数据库 | Business DB | 被查询和分析的真实数据源 |
| 查询组件 | Saved Query | 用户在工作台保存的 SQL、图表类型、宏变量和阈值配置 |
| 看板 | Dashboard | 由多个查询组件组成的可视化画布 |
| 组件实例 | Widget | Dashboard 上引用某个 Saved Query 的具体布局实例 |
| 分析工作台 | Query Editor Workspace | 编写 SQL、执行查询、预览图表和保存组件的页面 |
| 配置中心 | Data Sources | 管理数据源连接配置的页面 |
| 明细穿透 | Drill-through | 从聚合结果点击进入底层明细数据 |
| 聚合下钻 | Drill-down | 在多维分析中替换维度并保留指标继续聚合分析 |
| 智能投影 | Smart Projection | 根据点击指标类型自动决定明细查询投影方式 |
| 宏变量 | Macro | SQL 中形如 `{{version}}` 的动态占位符 |
| 全局宏 | Global Macro | Dashboard 级别统一传入多个 Widget 的宏变量 |
| 局部宏 | Local Macro | Saved Query 或 Widget 自身配置的宏变量 |
| 阈值规则 | Threshold | 对表格指标进行条件高亮的规则 |
| 物理外键 | Physical Foreign Key | 数据库层面的外键约束；当前元数据表不使用 |
| 逻辑聚合 | Logical Aggregation | Repository 通过查询和组装实现实体关联 |
| AST | Abstract Syntax Tree | SQL 解析后的抽象语法树 |
| sqlglot | sqlglot | 后端用于解析和重写 SQL 的库 |
| ClickHouse | ClickHouse | 当前主要业务分析数据库适配器 |
| DuckDB | DuckDB | 当前本地分析数据库适配器 |
| `x-data-source-id` | Header | 后端用于指定查询数据源的 HTTP 请求头 |
| `QueryResult` | DTO | 后端查询结果结构，包含 `columns`、`data`、`total` |
| `DrillThroughRequest` | DTO | 明细穿透请求结构，包含原 SQL、过滤上下文、点击指标、宏变量和分页 |

## 后续术语追加区

```text
| 术语 | 英文 / 代码名 | 定义 |
| :--- | :--- | :--- |
|  |  |  |
```

