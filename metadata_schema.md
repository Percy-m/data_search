# 元数据数据库字典 (Metadata Schema)

本文档记录了平台用于存储自身配置的元数据表结构（默认运行于后端的 PostgreSQL 中）。

**注意：** 任何对于 `back-end/infrastructure/orm_models.py` 中模型结构的修改，都**必须**同步更新此文档。

---

## 1. 数据源表 (`data_sources`)
用于存储用户接入的各类业务数据库的连接信息。

| 字段名 | 数据类型 | 属性 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 唯一主键 |
| `name` | String(100) | Not Null, Unique | 连接名称 (如: 生产库-ClickHouse) |
| `type` | String(50) | Not Null | 数据库类型标识 (如: `clickhouse`, `mysql`) |
| `host` | String(255) | Not Null | 主机地址或 IP |
| `port` | Integer | Not Null | 端口号 |
| `username` | String(100) | Nullable | 登录用户名 |
| `password` | String(255) | Nullable | 登录密码 (实际生产应加密存储) |
| `database` | String(100) | Nullable | 默认连接库名 |
| `created_at` | DateTime | Default UTC Now | 记录创建时间 |

---

## 2. 查询组件表 (`saved_queries`)
存储分析师在“工作台”固化的原生 SQL 片段及其图表化配置，是构成看板的基础零件 (Widget)。

| 字段名 | 数据类型 | 属性 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 唯一主键 |
| `name` | String(255) | Not Null, Unique | 组件/查询的业务名称 |
| `data_source_id` | Integer | Nullable, Index | 该查询关联的数据源 ID |
| `raw_sql` | Text | Not Null | 固化的原生 SQL 语句 |
| `macros` | JSON | Default `[]` | 查询内部定义的宏变量 (如 `{{version}}`) 的默认配置 |
| `thresholds` | JSON | Default `[]` | 指标条件高亮染色规则 |
| `chart_type` | String(50) | Default `'table'` | 该查询关联的可视化类型 (`table`, `bar`, `pie`, `line`) |
| `created_at` | DateTime | Default UTC Now | 记录创建时间 |

---

## 3. 看板画布表 (`dashboards`)
存储用户创建的数据看板（Dashboard）的壳信息。

| 字段名 | 数据类型 | 属性 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 唯一主键 |
| `name` | String(255) | Not Null, Unique | 看板名称 |
| `description` | Text | Nullable | 看板描述 / 备注 |
| `created_at` | DateTime | Default UTC Now | 记录创建时间 |

---

## 4. 数据对比配置表 (`comparison_configs`)
保存独立“数据对比”栏目中的对比任务配置。该表不复用 `saved_queries`，避免污染单查询/单 Widget 假设。

| 字段名 | 数据类型 | 属性 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 唯一主键 |
| `name` | String(255) | Not Null, Unique, Index | 对比配置名称 |
| `data_source_id` | Integer | Nullable, Index | 该对比关联的数据源 ID |
| `raw_sql` | Text | Not Null | 被对比的原始 SQL；baseline/target 使用同一 SQL |
| `baseline_name` | String(100) | Default `'baseline'` | 基线侧展示名称 |
| `target_name` | String(100) | Default `'target'` | 目标侧展示名称 |
| `baseline_macros` | JSON | Default `{}` | baseline 侧宏变量字典 |
| `target_macros` | JSON | Default `{}` | target 侧宏变量字典 |
| `key_columns` | JSON | Default `[]` | 用于对齐两侧结果的主键列列表 |
| `group_columns` | JSON | Default `[]` | 汇总分组列列表 |
| `criteria` | JSON | Default `[]` | 对比标准列表，包含名称、比较列、比较方式和容差 |
| `compare_columns` | JSON | Default `[]` | 兼容简化配置的比较列列表 |
| `max_rows` | Integer | Default `100000` | 单侧最大拉取行数，超过即拒绝对比 |
| `created_at` | DateTime | Default UTC Now | 记录创建时间 |

---

## 5. 看板布局明细表 (`dashboard_widgets`)
记录某一个具体看板 (`dashboards.id`) 上摆放了哪些组件 (`saved_queries.id`)，以及它们在无限画布上的绝对坐标和长宽。

| 字段名 | 数据类型 | 属性 | 描述 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | PK, Auto Increment | 唯一主键 |
| `dashboard_id` | Integer | Not Null, Index | 关联所属的数据看板 |
| `query_id` | Integer | Not Null, Index | 关联被引入的查询组件 |
| `x` | Integer | Default `0` | 画布 X 轴坐标 (列位置) |
| `y` | Integer | Default `0` | 画布 Y 轴坐标 (行位置) |
| `w` | Integer | Default `12` | 组件宽度 (占据的网格列数) |
| `h` | Integer | Default `8` | 组件高度 |
| `i` | String(50) | Not Null | 前端 `vue-grid-layout` 所需的唯一区块实例标识符 |
