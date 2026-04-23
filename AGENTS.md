# Agent Instructions

## Environment & Execution

- **Backend (Python 3.9 + FastAPI)**:
  - Located in the `back-end/` directory.
  - Run with: `cd back-end && .venv/bin/python main.py` or `cd back-end && .venv/bin/python -m uvicorn main:app --reload`.
  - Use the local `back-end/.venv` directory for all Python package management and command execution.
- **Metadata Database (PostgreSQL)**:
  - Managed via Docker Compose in the root directory (`docker-compose up -d`). 
  - Essential for storing data sources, saved queries, and dashboard layouts.
- **Frontend (Vue 3 + Vite)**:
  - Located in the `front-end/` directory.
  - Run with: `cd front-end && npm run dev`.
  - Core stack includes Element Plus, ECharts (`vue-echarts`), `vue3-grid-layout` for dashboards, and `exceljs` for style-aware exporting.
- **IDE**: PyCharm project. Ignore the `.idea/` directory unless specifically asked.

## Architecture & Conventions (Backend)

The system strictly follows a **Ports and Adapters (Hexagonal) Architecture** to remain database-agnostic.

- `back-end/core/`: 
  - Pure domain models (`models.py`) and interface definitions (`ports.py`). 
  - PostgreSQL ORM models (`meta_models.py`) mapping to configurations (DataSource, SavedQuery, Dashboard).
- `back-end/adapters/`: Concrete implementations of `core/ports.py` (e.g., `ClickHouseAdapter`). All DB-specific SQL translation and connection logic lives here.
- `back-end/services/`: Core business logic (`QueryService`). Operates purely on the `DataSourcePort` interface.
- `back-end/api/`: FastAPI route definitions and dependency injection. It dynamically instantiates the correct `DataSourcePort` adapter via `x-data-source-id` header fetching config from PostgreSQL.

## Query & Drill-down Design

- **AST over SQL**: The query system relies heavily on parsing raw SQL into an Abstract Syntax Tree (AST) using `sqlglot`.
- **Smart Projection (Drill-through / 明细穿透)**:
  - When clicking on metrics in ECharts or Tables to see underlying raw data, the frontend sends the SQL and clicked metric.
  - The backend safely extracts `FROM`, `JOIN`s, and `WHERE` using `sqlglot`.
  - **COUNT(DISTINCT)** handling: Instead of just blowing up into a large base table (`SELECT *`), if a `COUNT(DISTINCT table.field)` is clicked, the backend modifies the projection to `SELECT table.*` and appends `LIMIT 1 BY table.field` to precisely return the deduped underlying entity rows without metric distortion.
- **Dynamic Table Mapping (Macro Variables)**: 
  - Supports passing a `macros: Dict[str, str]` object from the frontend (e.g., `{"version": "3_1"}`).
  - Backend uses `sqlglot` to traverse the AST, finds `Table` nodes containing placeholders like `{{version}}`, and safely injects the macro values directly into the AST structure (e.g., transforming `order_{{version}}` to `order_3_1`) before executing. This avoids fragile string replacements and prevents accidental manipulation of aliases or column names.

## Testing & Tooling

- There are currently no established test suites, linters, or formatters configured in `pyproject.toml` or `package.json`. Do not proactively introduce arbitrary ones without explicit user direction.