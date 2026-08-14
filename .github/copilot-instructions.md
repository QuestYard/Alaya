# Copilot Instructions for Alaya

## Build, run, lint, and test commands

- Install dependencies: `uv sync`
- Install with dev dependencies: `uv sync --dev`
- Run the app entrypoint: `uv run alaya`
- Run the CLI chat workbench: `uv run alaya-chat`
- Initialize or reset the MySQL schema: `uv run alaya-init`
- Build distributables: `uv build`
- Type-check: `uvx pyright`
- Lint: `uvx ruff check .`
- Tests: there is currently no automated test suite checked into this repository; validate with type checking and linting.

## High-level architecture

- **Layout & Packaging**: Standard Python `src/` layout under `src/alaya/`. Console scripts `alaya` (`alaya.main:start`) and `alaya-init` (`alaya.init_cli:main`) defined in `pyproject.toml`.
- **Runtime Configuration & Initialization**:
  - `src/alaya/__init__.py` executes initialization on import: loads `.env`, parses `alaya.yaml` via `dict_to_namespace`, validates required keys (`db.user`, `db.password`, `db.database`, `service.agent_model`), sets defaults, and configures global `logger` and `conf`.
  - Configuration structure is documented in `alaya-config_template.yaml`, including `db`, `app`, hierarchical `retrieval` (`output_limits` and `quality_profiles`), and `service` (`hurag_server`, `agent_model`).
- **Database & Persistence (`src/alaya/rss.py`)**:
  - Centralized MySQL persistence using `aiomysql` connection pooling.
  - Standard helpers: `get_pool`, `with_rdb`, `query`, `query_iter`, `dml`, and `transact`.
  - DDL bootstrap statements live in `src/alaya/constants.py` (`INIT_RSS_SCRIPTS`) and are executed by `src/alaya/init_cli.py`.
- **HuRAG Backend Client (`src/alaya/hurag.py`)**:
  - Manages async HTTP client connection pools (`httpx.AsyncClient`) communicating with HuRAG API server for vector search, graph search, document reading, and streaming LLM chat.
- **Agent Layer (`src/alaya/agents/`)**:
  - `alaya_agent.py`: Pydantic AI Agent (`Agent[AgentDeps, str]`) with `AgentDeps` (`user: User`, `client: AsyncClient`).
  - Implements 6 specialized tools: `list_documents`, `search_evidence` (unified text/graph/both hybrid retrieval with quality profiles), `search_text_evidence`, `read_text_document`, `read_multimodal_document`, and `read_attachment`.
  - `history_manager.py`: Context window estimation and automatic history compression for multi-turn conversations across CLI and Web UI (supporting `tiny: ~4K`, `medium: ~32K`, `large: ~256K`).
  - `system_prompt.py`: Detailed enterprise knowledge base QA system prompt (`SYSTEM_PROMPT`).
- **Full-Text Session Search (`src/alaya/fts/`)**:
  - `tokenizer.py`: `pkuseg`-based Chinese word segmentation with spawn-context `ProcessPoolExecutor` parallel tokenization.
  - `retriever.py`: In-memory BM25 index (`bm25s`) over user chat histories for instant session search.
- **Service Layer (`src/alaya/services/`)**:
  - `session_service.py`: Session CRUD, message history, sequence locking, citation persistence, and LLM-assisted session title generation.
  - `user_service.py` & `sso.py`: User authentication, password management, and SSO integration.
  - `citation_service.py`: Knowledge citation tracking.
- **UI & Viewer Layer (`src/alaya/viewers/` & `src/alaya/main.py`)**:
  - Built with NiceGUI and FastAPI.
  - `events.py`: `ClientEvents` decoupled event bus connecting UI actions with state handlers.
  - `chat_viewer.py`, `session_viewer.py`, `citation_viewer.py`, `user_viewer.py`: Modular NiceGUI components for the interactive workbench (session drawers, chat messages, citation drawer, user dialogs).
- **CLI Workbench (`src/alaya/cli/`)**:
  - `chat_cli.py`: Interactive terminal-based chat client (`alaya-chat`) powered by Typer and Rich. Supports multi-turn conversations, virtual user setup via `CLI_USER_PATH`, `/new`, `/exit`, `/clear`, `/tokens` slash commands, and streaming output (thinking part in dim italic, tool notifications without raw results, and markdown final responses).

## Key repository conventions

- **Execution & Tools**: Always prefer `uv` for package management and CLI commands. Use `uvx pyright` and `uvx ruff check .` for static checks.
- **Side Effects on Import**: `import alaya` loads `.env`, reads `alaya.yaml`, and configures global loggers from the current working directory. The project must be run from the repository root.
- **Globals**: Reuse the package globals `conf` and `logger` imported from `alaya`.
- **Config Access**: Config dictionaries are converted via `dict_to_namespace` in `utilities.py`; always access configuration fields with attribute syntax (e.g. `conf.retrieval.output_limits.both.segments`).
- **Database Operations**: Always use helpers from `src/alaya/rss.py` for connection management, transaction safety, and pooling.
- **Data Model Updates**: DDL definitions belong in `src/alaya/constants.py` (`INIT_RSS_SCRIPTS`).

