# 业务规则文档 (Business Rules)

本文档记录用户侧确认的业务规则、指标口径和交互约定。后续需求涉及业务含义变化时，必须先更新本文档。

## 1. 数据源规则

- 数据源配置必须先通过后端连接测试，成功后才能保存。
- ClickHouse 数据源使用 Host、Port、Username、Password、Database 连接。
- DuckDB 数据源使用 `database` 字段作为文件路径；为空时视为内存模式。
- 数据源密码编辑时，前端留空表示不修改原密码。
- 查询执行时优先使用请求头 `x-data-source-id` 指定的数据源；未指定时走后端默认开发配置。

## 2. SQL 与宏变量规则

- Saved Query 保存的是原生 SQL，不要求前端把 SQL 转换成结构化查询模型。
- 宏变量使用 `{{key}}` 语法。
- 宏变量替换发生在后端 `QueryService`，并且必须早于 AST 解析。
- 宏变量值只允许安全白名单字符：英文字母、数字、下划线、短横线、点号和中文。
- 宏变量不得包含单引号、双引号、分号、注释符等可能破坏 SQL 结构的字符。
- 宏变量可以用于动态表名、动态分区、动态筛选值等场景。

## 3. 查询结果规则

- 查询结果统一返回 `columns`、`data`、`total`。
- `total = -1` 表示后端未计算总数或该查询不支持总数。
- 原生 SQL 分页由后端在解析后的基础 SQL 外追加 `LIMIT` 和 `OFFSET`。
- 高频原生查询可以命中单 Worker 内存缓存，缓存键必须包含数据源、SQL 和分页等参数。

## 4. 图表规则

- 当前支持 `table`、`bar`、`line`、`pie` 四种展示类型。
- 图表默认使用结果集第一列作为维度列，其余列作为指标列。
- 表格指标列可点击触发明细穿透。
- ECharts 图形元素点击时，以当前图形点所在行和 series 名称推导穿透上下文。

## 5. 看板规则

- Dashboard 是 Widget 布局容器。
- Widget 引用 Saved Query，布局信息存储在 `dashboard_widgets`。
- 元数据表不使用物理外键，关联清理由 Repository 显式处理。
- 看板编辑模式允许拖拽、缩放、添加、删除组件。
- 非编辑模式用于稳定浏览和明细穿透。
- 看板全局宏从组件宏配置中提取，并可覆盖 Widget 默认宏值。

## 6. 明细穿透规则

- 前端不得自行拼接明细 SQL。
- 明细穿透必须由后端基于 `sqlglot` 提取原 SQL 的 `FROM`、`JOIN`、`WHERE`。
- 普通聚合指标默认穿透为底层宽表明细。
- `COUNT(DISTINCT table.field)` 应尽量投影为对应实体表，并使用 ClickHouse `LIMIT 1 BY table.field` 语义去重。
- 明细穿透必须保留原 SQL 的基础过滤条件，并叠加用户点击行产生的维度过滤条件。
- 明细穿透结果必须支持分页。

## 7. 阈值与导出规则

- 阈值规则绑定列名、操作符、阈值和颜色。
- 支持 `>`、`<`、`=`、`>=`、`<=`、`between`、`not_between`。
- 深色背景应自动切换为浅色文字，保证可读性。
- Excel 导出应尽量保留表格数据和阈值样式。

## 8. 数据对比规则

- 数据对比配置是独立元数据对象，不保存为 Saved Query，也不作为 Dashboard Widget 使用。
- 第一版只支持同一 SQL 在 baseline 和 target 两组宏参数下的输出结果对比。
- 对比发生在 SQL 输出结果集层面；复杂 JOIN、聚合和计算字段均由用户 SQL 决定。
- baseline 与 target 输出列名必须一致，主键列、分组列和比较列均引用输出列名。
- 主键列组合必须在 baseline 和 target 各自结果集中唯一；重复 key 必须拒绝运行。
- 仅 baseline 存在的 key 计为 `target_missing`，仅 target 存在的 key 计为 `baseline_missing`。
- 汇总一致率按 `matched_count / (matched_count + mismatched_count)` 计算，缺失单独展示。
- 单侧默认最大对比行数为 `100000`，超过时后端中止并提示缩小 SQL 范围。
- 对比明细展示 key、分组、baseline/target 值、差值、变化率、差异字段和状态，不继续触发原始底表 Drill-through。

## 9. 后续规则追加区

后续新增规则按以下格式追加：

```text
### BR-YYYYMMDD-001 规则标题
- 适用模块：
- 规则说明：
- 例外情况：
- 影响的验收标准：
```
