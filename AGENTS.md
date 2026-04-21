# Agent Instructions

## Environment & Execution

- **Backend (Python 3.9 + FastAPI)**:
  - Located in the `back-end/` directory.
  - Run with: `cd back-end && .venv/bin/python main.py` or `cd back-end && .venv/bin/python -m uvicorn main:app --reload`.
  - Use the local `back-end/.venv` directory for all Python package management and command execution.
- **Frontend (Vue 3 + Vite)**:
  - Located in the `front-end/` directory.
  - Run with: `cd front-end && npm run dev`.
  - Uses Element Plus and ECharts.
- **IDE**: PyCharm project. Ignore the `.idea/` directory unless specifically asked.

## Architecture & Conventions (Backend)

The system strictly follows a **Ports and Adapters (Hexagonal) Architecture** to remain database-agnostic.

- `back-end/core/`: Pure domain models (`models.py`) and interface definitions (`ports.py`). **Must not** depend on concrete DBs, external web frameworks, or DB clients.
- `back-end/adapters/`: Concrete implementations of `core/ports.py` (e.g., `ClickHouseAdapter`). All DB-specific SQL translation and connection logic lives here.
- `back-end/services/`: Core business logic (`QueryService`). Operates purely on the `DataSourcePort` interface.
- `back-end/api/`: FastAPI route definitions and dependency injection (instantiating the correct adapter based on config).

## Query & Drill-down Design

- **AST over SQL**: The query system uses a structured AST (dimensions, metrics, filters) defined via Pydantic in `back-end/core/models.py`. 
- **Raw SQL & sqlglot**: While AST is preferred, users can execute Raw SQL. To support secure interactions (like drill-through/viewing details) on Raw SQL results, the backend uses `sqlglot` to parse Raw SQL strings safely, extracting contexts like `FROM` and `WHERE` without relying on fragile frontend regex.
- **Drill-down vs Drill-through**:
  - **Drill-down (下钻)**: A structural transformation replacing dimensions and appending current-level filters to a base AST query.
  - **Drill-through (明细穿透)**: Parses a raw SQL query using `sqlglot` to extract its base table and conditions, then appends row-level filters to generate a `SELECT *` query with pagination for raw data inspection.

## Testing & Tooling

- There are currently no established test suites, linters, or formatters configured in `pyproject.toml` or `package.json`. Do not proactively introduce arbitrary ones without explicit user direction.