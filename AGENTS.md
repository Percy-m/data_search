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

- **AST over SQL**: The query system uses a structured AST (dimensions, metrics, filters) defined via Pydantic in `back-end/core/models.py`. Avoid passing raw SQL strings through the service layer.
- **Generic Drill-down**: Drill-down logic (`QueryService.drill_down`) is a pure structural transformation. It replaces dimensions and appends current-level filters to the base query, keeping it independent of specific tables or business fields.

## Testing & Tooling

- There are currently no established test suites, linters, or formatters configured in `pyproject.toml` or `package.json`. Do not proactively introduce arbitrary ones without explicit user direction.