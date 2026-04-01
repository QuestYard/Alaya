import os
from . import logger, conf

src_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(src_dir, "static")


# Helper to get static asset path
def asset(name):
    return os.path.join(static_dir, name)


# --- NiceGUI App Setup ---
async def _startup_app() -> None:
    logger.info("Starting up Alaya WebUI App...")

    logger.info("Creating database connection pool ...")
    from . import rss

    await rss.get_pool()

    # logger.info("Creating LLM chat client ...")
    # from ..llm import get_oa_client

    # await get_oa_client(client_name=oa_client_name)

    logger.info("Alaya WebUI App startup completed.")


async def _shutdown_app() -> None:
    from ..dss import rss

    logger.info("Closing database connection pool...")
    await rss.close_pool()
    from ..llm import close_oa_client

    logger.info("Closing chat completions client...")
    await close_oa_client()
    logger.info("HuRAG WebUI App shutdown completed.")


# Register startup and shutdown handlers
app.on_startup(_startup_app)
app.on_shutdown(_shutdown_app)

# Mount static directory to serve static files like favicon.svg
# You can now access your icon at: http://localhost:8082/static/favicon.svg
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Get storage secret from environment
storage_secret = os.environ.get("STORAGE_SECRET")
if not storage_secret:
    logger.warning("STORAGE_SECRET is not set. Using a default (insecure) value.")
    storage_secret = "default_secret_please_change"


# --- App Entry Point ---

def start():
    print(
        "The Alaya-vijbana is constantly flowing and will eventually transform "
        "into wisdom."
    )
#     try:
#         ui.run(
#             root=root,
#             title="HuRAG WebUI - A ChatBot",
#             host=conf.webui_app.host,
#             port=conf.webui_app.port,
#             reload=__name__ in {"__main__", "__mp_main__"},
#             uvicorn_reload_dirs=src_dir,
#             favicon=asset("favicon.ico"),
#             storage_secret=storage_secret,
#         )
#     except KeyboardInterrupt:
#         pass


if __name__ in {"__main__", "__mp_main__"}:
    start()
