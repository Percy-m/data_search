# Agent Instructions

## Core Rules (Must Follow)

- **Language**: 所有与用户的对话和回答**必须使用中文**。
- **Version Control**: 每次任务执行完毕或完成一个逻辑闭环后，必须进行 `git commit`。
- **Documentation Sync**: 
  - 修改 `back-end/infrastructure/orm_models.py` (PostgreSQL 表结构) 后，必须同步更新 `metadata_schema.md`。
  - 涉及系统架构、模块职责或部署拓扑的改动，必须同步更新 `4_plus_1_views.md` 中的 PlantUML 代码。
  - 任务完成后，检查并更新 `AGENTS.md` 或 `README.md` 以保持文档最新。
- **Local DB Connection**: 本机 ClickHouse 客户端一律采用 `clickhouse client` 命令进行连接和查询。

## Environment & Execution

- **Backend (Python 3.9 + FastAPI)**:
  - Directory: `back-end/`
  - Run Server: `cd back-end && .venv/bin/python -m uvicorn main:app --reload`
  - Package Management: Use the local `back-end/.venv` environment (e.g., `back-end/.venv/bin/pip`).
- **Frontend (Vue 3 + Vite)**:
  - Directory: `front-end/`
  - Run Dev Server: `cd front-end && npm run dev`
  - Core Stack: Element Plus, ECharts (`vue-echarts`), `vue3-grid-layout`, `exceljs`.
- **Metadata Database (PostgreSQL)**:
  - Managed via Docker Compose (`docker-compose up -d` in root). Essential for data sources, saved queries, and dashboards.
- **IDE**: PyCharm project. Ignore the `.idea/` directory.

## Backend Architecture (Hexagonal)

- `back-end/core/`: Pure domain models (`models.py`), interface definitions (`ports.py`).
- `back-end/infrastructure/`: PostgreSQL ORM models (`orm_models.py`) and implementations (`repositories.py`).
  - **No Physical Foreign Keys**: Physical foreign keys have been stripped from `orm_models.py`. Logical aggregation is handled in `repositories.py`.
- `back-end/adapters/`: Concrete DB implementations (e.g., `clickhouse.py`, `duckdb.py`). All SQL translation lives here.
- `back-end/services/`: Core business logic (`query.py`). Operates purely on `DataSourcePort`.
- `back-end/api/`: FastAPI routes. Dynamically instantiates the correct adapter via `x-data-source-id` header fetching config from PostgreSQL.

## Frontend Architecture

- **Performance with Large Data**: Vue's deep Proxy (`reactive`, `ref`) creates severe performance bottlenecks with large datasets or grid components. 
  - **CRITICAL**: Must use `shallowReactive` and `markRaw` for large data arrays and ECharts/Grid items to ensure the `vue3-grid-layout` drag-and-drop engine remains performant.

## Query & Drill-down Design

- **AST over SQL**: Relies heavily on parsing raw SQL into an AST using `sqlglot`.
- **Smart Projection (Drill-through / 明细穿透)**:
  - Safely extracts `FROM`, `JOIN`s, and `WHERE` using `sqlglot`.
  - **COUNT(DISTINCT)** handling: Modifies projection to `SELECT table.*` and appends `LIMIT 1 BY table.field` to return deduped rows without metric distortion.
- **Dynamic Table Mapping (Macro Variables)**: 
  - Frontend passes `macros: Dict[str, str]`.
  - **CRITICAL**: Backend uses **string-level pre-compilation (regex whitelist)** in `QueryService` *before* AST parsing, **not** AST replacement. This is because `{}` (e.g., `{{version}}`) is incorrectly parsed as Map/Dictionary literals by `sqlglot` in ClickHouse dialect, breaking the AST.

## Testing & Tooling

- **No Toolchain**: There are currently no established test suites, linters, or formatters. Do not proactively introduce arbitrary ones without explicit user direction.
- **Acceptance Criteria**: Refer to `TEST_PLAN.md` for business scenario checklists and manual acceptance test criteria.
