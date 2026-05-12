# 数据对比设计

## 后端

- 元数据表：`comparison_configs` 保存独立对比配置，包含数据源、SQL、两侧宏变量、主键列、分组列、对比标准和最大行数。
- API：
  - `POST /api/v1/comparisons/`
  - `GET /api/v1/comparisons/`
  - `GET /api/v1/comparisons/{id}`
  - `PUT /api/v1/comparisons/{id}`
  - `DELETE /api/v1/comparisons/{id}`
  - `POST /api/v1/data/compare`
  - `POST /api/v1/data/compare/detail`
- 服务：`ComparisonService` 通过 `QueryService.raw_query()` 分别执行 baseline 与 target，因此复用宏变量白名单、安全 SQL 执行和缓存。
- 算法：
  - 以主键列组合建立 baseline/target 索引，任何一侧出现重复主键即拒绝运行。
  - 两侧都有的 key 按每个对比标准计算一致或不一致。
  - 仅 target 存在计为 `baseline_missing`；仅 baseline 存在计为 `target_missing`。
  - 汇总按分组列和对比标准聚合，一致率为 `一致 / (一致 + 不一致)`，缺失单独展示。

## 前端

- 新增 `ComparisonWorkspace.vue`，由 `BiDashboard.vue` 挂载为独立标签页。
- 大结果容器使用 `shallowRef`，避免对汇总和明细数组做深层响应式代理。
- 配置区包含 SQL、宏变量、主键列、分组列、对比标准、运行/保存/更新/导出按钮。
- 结果区展示汇总表，点击计数字段调用明细接口并打开弹窗。
