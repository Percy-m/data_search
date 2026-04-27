# Agent Instructions

## Core Rules (Must Follow)

- **Language**: 所有与用户的对话和回答**必须使用中文**。
- **Version Control**: 每次任务执行完毕或完成一个逻辑闭环后，必须进行 `git commit`。
- **Documentation Sync**: 
  - 修改 `back-end/core/meta_models.py` (PostgreSQL 表结构) 后，必须同步更新 `metadata_schema.md`。
  - 涉及系统架构、模块职责或部署拓扑的改动，必须同步更新 `4_plus_1_views.md` 中的 PlantUML 代码。
  - 任务完成后，检查并更新 `AGENTS.md` 或 `README.md` 以保持文档最新。
- **Local DB Connection**: 本机 ClickHouse 客户端一律采用 `clickhouse client` 命令进行连接和查询。

## Environment & Execution

- **Backend (Python 3.9 + FastAPI)**:
  - Directory: `back-end/`
  - Run Server: `cd back-end && .venv/bin/python main.py` or `cd back-end && .venv/bin/python -m uvicorn main:app --reload`.
  - Package Management: Use the local `back-end/.venv` environment (e.g., `back-end/.venv/bin/pip`).
- **Frontend (Vue 3 + Vite)**:
  - Directory: `front-end/`
  - Run Dev Server: `cd front-end && npm run dev`.
  - Core Stack: Element Plus, ECharts (`vue-echarts`), `vue3-grid-layout`, `exceljs`.
- **Metadata Database (PostgreSQL)**:
  - Managed via Docker Compose (`docker-compose up -d` in root). Essential for data sources, saved queries, and dashboards.
- **IDE**: PyCharm project. Ignore the `.idea/` directory.

## Architecture & Conventions (Backend)

Follows **Ports and Adapters (Hexagonal) Architecture** to remain database-agnostic. Code should ensure high availability, scalability, and domain abstraction.

- `back-end/core/`: Pure domain models (`models.py`), interface definitions (`ports.py`), and PostgreSQL ORM models (`meta_models.py`).
- `back-end/adapters/`: Concrete DB implementations (e.g., `clickhouse.py`). All SQL translation lives here.
- `back-end/services/`: Core business logic (`query.py`). Operates purely on `DataSourcePort`.
- `back-end/api/`: FastAPI routes. Dynamically instantiates the correct adapter via `x-data-source-id` header fetching config from PostgreSQL.

## Query & Drill-down Design

- **AST over SQL**: Relies heavily on parsing raw SQL into an AST using `sqlglot`.
- **Smart Projection (Drill-through / 明细穿透)**:
  - Safely extracts `FROM`, `JOIN`s, and `WHERE` using `sqlglot`.
  - **COUNT(DISTINCT)** handling: Modifies projection to `SELECT table.*` and appends `LIMIT 1 BY table.field` to return deduped rows without metric distortion.
- **Dynamic Table Mapping (Macro Variables)**: 
  - Frontend passes `macros: Dict[str, str]`.
  - Backend uses `sqlglot` to find `Table` nodes with placeholders (e.g., `{{version}}`) and injects macro values directly into the AST structure.

## Testing & Tooling

- There are currently no established test suites, linters, or formatters. Do not proactively introduce arbitrary ones without explicit user direction.
