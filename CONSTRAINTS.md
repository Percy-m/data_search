# 项目约束 (Constraints)

本文档记录用户侧确认的技术、业务、运行和协作约束。后续需求如果要突破约束，必须先更新本文档。

## 1. 协作约束

- 所有与用户的对话和最终回答必须使用中文。
- 每次任务完成或形成逻辑闭环后必须执行 `git commit`。
- 工作区可能存在用户未跟踪或未提交文件，不得擅自删除、回退或覆盖。
- `.idea/` 目录忽略。

## 2. 文档同步约束

- 修改 `back-end/infrastructure/orm_models.py` 后，必须同步更新 `metadata_schema.md`。
- 涉及系统架构、模块职责或部署拓扑变化时，必须同步更新 `4_plus_1_views.md` 中的 PlantUML。
- 涉及运行方式、依赖或主要能力变化时，必须检查并更新 `README.md`。
- 涉及前端运行方式变化时，必须检查并更新 `front-end/README.md`。
- 采用 SDD 后，新需求应先补充用户侧文档，再生成具体规格。

## 3. 后端约束

- 后端目录为 `back-end/`。
- Python 环境使用 `back-end/.venv`。
- 启动命令为 `cd back-end && .venv/bin/python -m uvicorn main:app --reload`。
- 后端遵循六边形架构：
  - `core/` 保持领域模型和接口定义。
  - `services/` 保持业务逻辑。
  - `adapters/` 负责具体数据库实现和 SQL 方言。
  - `infrastructure/` 负责 PostgreSQL ORM 和仓储。
  - `api/` 负责 HTTP 路由。
- 新数据源应通过 `DataSourcePort` 和 `DataSourceFactory` 扩展。
- SQL 宏替换必须保留在 `QueryService` 的 AST 解析之前。

## 4. 前端约束

- 前端目录为 `front-end/`。
- 启动命令为 `cd front-end && npm run dev`。
- 技术栈为 Vue 3 + Vite + Element Plus + ECharts + `vue3-grid-layout` + ExcelJS。
- 大结果集和看板组件状态应使用 `shallowReactive` / `shallowRef`。
- 引入不可变 ECharts 配置或第三方实例时，应考虑 `markRaw`。
- 前端不得自行拼接 Drill-through 明细 SQL。

## 5. 数据库约束

- PostgreSQL 元数据库通过 Docker Compose 管理。
- 元数据 ORM 模型不使用物理外键。
- 元数据关联清理由 Repository 显式处理。
- 本机 ClickHouse 客户端连接和查询必须使用 `clickhouse client` 命令。

## 6. 测试与工具约束

- 当前没有既定自动化测试、lint 或 formatter 工具链。
- 不应在没有明确需求时主动引入新的测试框架、lint 或 formatter。
- 手动验收参考 `TEST_PLAN.md` 和 `ACCEPTANCE_CRITERIA.md`。

## 7. 安全约束

- 宏变量必须通过白名单校验。
- 不得把包含危险字符的宏值送入数据库执行。
- 数据源密码当前存储在元数据库中，生产化前需要重新评估加密和权限策略。
- 当前 CORS 配置偏向本地开发，生产化前必须收紧。

## 8. 后续约束追加区

```text
### CS-YYYYMMDD-001 约束标题
- 类型：业务 / 技术 / 安全 / 部署 / 协作
- 约束内容：
- 允许例外：
- 变更审批：
```

