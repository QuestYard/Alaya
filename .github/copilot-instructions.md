# Copilot Instructions for Alaya

## Build, run, lint, and test commands

- Install dependencies: `uv sync`
- Install with dev dependencies: `uv sync --dev`
- Run the app entrypoint: `uv run alaya`
- Initialize or reset the MySQL schema: `uv run alaya-init`
- Build distributables: `uv build`
- Type-check: `uvx pyright`
- Lint: `uvx ruff check .`
- Tests: there is currently no automated test suite checked into this repository, so there is no supported single-test command yet

## High-level architecture

- This is a Python `src/` layout project with the package in `src/alaya/`. The published console scripts are `alaya` and `alaya-init`, both defined in `pyproject.toml`.
- Importing `alaya` has important side effects. `src/alaya/__init__.py` loads `.env`, reads `alaya.yaml`, validates required config, applies defaults, and configures the global `logger` and `conf` objects at import time.
- Runtime configuration is centered on `alaya.yaml`, with the expected structure documented in `alaya-config_template.yaml`. Required fields include `db.user`, `db.password`, `db.database`, and `service.agent_model`.
- Database access is centralized in `src/alaya/rss.py`. It manages shared `aiomysql` pools and provides the preferred helpers for persistence work: `with_rdb`, `query`, `query_iter`, `dml`, and `transact`.
- Database schema bootstrap lives in `src/alaya/constants.py` as `INIT_RSS_SCRIPTS`, and `src/alaya/init_cli.py` executes those statements after an interactive confirmation prompt.
- `src/alaya/main.py` is the app entrypoint exposed as `alaya`. Right now it is mostly a stub that prints a startup message, but the commented code shows the intended runtime shape: a NiceGUI-based web UI driven by config from `conf`.
- The dependency set in `pyproject.toml` shows the broader intended architecture: NiceGUI/FastAPI web serving, MySQL-backed session storage, OpenAI and `pydantic-ai` integration, and retrieval-related components such as Milvus, BM25, and `pkuseg`, even though most of that pipeline is not yet wired into the checked-in Python code.

## Key repository conventions

- Prefer `uv` for environment and command execution. For static analysis in this repo, use `uvx pyright` and `uvx ruff check .`.
- Do not assume `import alaya` is cheap or side-effect free. Any code that imports package-level symbols will also trigger config loading and logger setup from the current working directory.
- Reuse the package globals instead of recreating them. Existing code expects modules to import `conf` and `logger` from `alaya`.
- Keep database logic inside the helpers in `src/alaya/rss.py` rather than opening ad hoc connections. Those helpers centralize pooling, cursor selection, commit/rollback behavior, and cleanup.
- The project expects to be run from the repository root because config and log paths are resolved with `Path.cwd()` (`alaya.yaml`, `.env`, and `alaya.log`).
- Configuration objects are accessed with attribute syntax, not raw dictionaries. `dict_to_namespace` in `src/alaya/utilities.py` converts nested config dictionaries into namespace objects, and the rest of the code relies on that access pattern.
- Schema and bootstrap SQL are treated as code constants. If the session/user/query data model changes, update `INIT_RSS_SCRIPTS` rather than scattering DDL elsewhere.
