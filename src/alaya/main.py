import os

from nicegui import ui, app
from fastapi.staticfiles import StaticFiles

from . import logger, conf
from .events import ClientEvents
from .constants import MAIN_PAGE_STYLES
from .models import User
from .services import (
    login,
    SSOUnavailableError,
    AccountNotExistsError,
)
from .viewers import (
    user_manager,
)


src_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(src_dir, "static")


# Helper to get static asset path
def asset(name):
    return os.path.join(static_dir, name)


# --- NiceGUI App Setup ---
async def _startup_app() -> None:
    logger.info("Starting up Alaya WebUI App...")

    logger.info("Creating database connection pool...")
    from . import rss
    await rss.get_pool()

    logger.info("Creating HuRAG API client...")
    from . import hurag
    await hurag.get_client()

    # logger.info("Creating LLM chat client ...")
    # from ..llm import get_oa_client

    # await get_oa_client(client_name=oa_client_name)

    logger.info("Alaya WebUI App startup completed.")


async def _shutdown_app() -> None:
    logger.info("Closing HuRAG API client...")
    from . import hurag
    await hurag.close_client()

    logger.info("Closing database connection pool...")
    from . import rss
    await rss.close_pool()

    # from ..llm import close_oa_client

    # logger.info("Closing chat completions client...")
    # await close_oa_client()

    logger.info("Alaya WebUI App shutdown completed.")


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
    try:
        ui.run(
            root=root,
            title="Alaya - Finally, it transforms into the wisdom.",
            host=conf.app.host,
            port=conf.app.port,
            reload=__name__ in {"__main__", "__mp_main__"},
            uvicorn_reload_dirs=src_dir,
            favicon=asset("favicon.ico"),
            storage_secret=storage_secret,
        )
    except KeyboardInterrupt:
        pass

# --- UI Page Definition ---


@ui.page("/")
async def root():
    # --- Initialize data in storage.browser (if any and only here)---
    client_events = ClientEvents()

    # Waiting for connection (storage.tab is available after connected)
    await ui.context.client.connected()

    # --- Custom Styling ---
    ui.add_css(MAIN_PAGE_STYLES)

    # --- Top Bar  ---
    with ui.header(bordered=True).classes(
        "items-center justify-between bg-white text-gray-800"
    ):
        # 1. Title and waiting spinner
        with ui.row().classes("items-center gap-2"):
            ui.label("Alaya - 知识恒久流转，终将转识成智").classes("text-h6")
            waiting_spinner = ui.spinner("bars", size="sm", color="zinc-500")
            waiting_spinner.set_visibility(False)
        # 2. Citation Button and Badge
        with ui.row().classes("items-center gap-2"):
            citation_btn = ui.button(icon="sym_r_book").props(
                "fab-mini flat color=gray-800"
            )
            with citation_btn:
                citations_badge = ui.badge(color="red-700", text_color="white").classes(
                    "pointer-events-none absolute top-1 right-1 "
                    "translate-x-1/3 -translate-y-1/3 "
                    "min-w-[16px] h-[16px] px-[4px] py-0 "
                    "flex items-center justify-center "
                    "rounded-full text-[10px] leading-none shadow"
                )
                ui.tooltip("隐藏引文").classes("text-caption")

    # --- Right drawer (references, citations, document viewer) ---
    citation_drawer = (
        ui.right_drawer(fixed=False, value=False)
        .props("width=420")
        .classes("border-l-1 border-gray-300")
    )
    with citation_drawer, ui.column().classes("fit no-wrap"):
        # 1. Drawer Title
        with ui.row().classes("w-full items-center"):
            ui.label("知识库引文").classes("text-subtitle1 font-bold")
            citation_spinner = ui.spinner("dots", color="zinc-500", size="sm")
            citation_spinner.set_visibility(False)
        # 2. Citations Card (to be filled dynamically)
        citations_card = (
            ui.card()
            .classes(
                "shadow-none border-0 w-full flex-grow overflow-y-auto mb-2 pl-0 pt-0"
            )
            .style(
                "mask-image: linear-gradient(to bottom, transparent, "
                "black 20px, black 90%, transparent);"
                "-webkit-mask-image: linear-gradient(to bottom, transparent, "
                "black 20px, black 90%, transparent);"
            )
        )

    # --- Left drawer (search menus, session history, settings, users) ---
    user_drawer = (
        ui.left_drawer(top_corner=True, bottom_corner=True, bordered=True)
        .props("width=240")
        .classes("bg-stone-50 px-2")
    )
    with user_drawer, ui.column().classes("w-full"):
        # 1. Logo and User Login Button
        with ui.row().classes("items-center justify-left w-full pl-2 gap-1 no-wrap"):
            ui.image(asset("favicon.ico")).classes("h-6 w-6")
            user_manager_lbl = ui.label().classes(
                "flex-grow min-w-0 rounded-lg p-2 cursor-pointer "
                "text-ellipsis no-underline text-gray-900 "
                "whitespace-nowrap overflow-hidden text-body1 "
                "hover:bg-neutral-200"
            )
        # 2. Menu Buttons
        with ui.column().classes("w-full gap-2"):
            new_session_btn = (
                ui.button("开始新对话", icon="sym_r_chat_add_on")
                .props("flat color=gray-600 align=left")
                .classes("w-full rounded-lg pl-2")
            )
            search_session_btn = (
                ui.button("搜索全部对话", icon="sym_r_search")
                .props("flat color=gray-600 align=left")
                .classes("w-full rounded-lg pl-2")
            )
        # 3. Session History (placeholder, at most 5 items and 'more...')
        with ui.column().classes("w-full my-2 gap-2 flex-grow overflow-y-auto"):
            with ui.row().classes("items-center justify-left w-full pl-2 gap-1"):
                ui.icon("sym_r_history").classes("text-gray-700 text-2xl")
                ui.label("最近对话").classes(
                    "text-subtitle2 font-bold text-gray-700 pl-2"
                )
            session_history_col = ui.column().classes("w-full gap-1 pl-8")

    # --- Main Content Area (chat messages, scrollable) ---
    with ui.column().classes("w-full absolute-full p-8"):
        # 1. The message_container contains chat messages, handle scrolling.
        message_container = ui.column().classes(
            "w-full max-w-4xl mx-auto px-4 items-stretch chat-scroll"
        )
        with message_container:
            ui.markdown("### 你想了解什么？").classes("text-center text-gray-900 mt-48")
        # 2. The input_container contains the input area and controls.
        input_container = ui.column().classes("w-full max-w-4xl mx-auto")
        with (
            input_container,
            ui.card().classes("w-full mx-auto mt-4 p-2 text-gray-700"),
        ):
            # 2.1. Text input area, scrollable, autogrow with max height
            with ui.card_section().classes("w-full p-0 max-h-32 overflow-y-auto"):
                text_input = (
                    ui.textarea(
                        "请输入您的问题...",
                        placeholder="按 Enter 发送消息, Shift+Enter 换行",
                    )
                    .props("autogrow clearable autofocus maxlength=2000")
                    .classes("w-full bg-white border-none shadow-none")
                )
            # 2.2. Bottom row with controls
            with ui.row().classes("w-full items-center justify-end px-2"):
                upload_btn = ui.button(icon="attach_file").props(
                    "flat round dense color=gray-500 size=md"
                )
                with upload_btn:
                    ui.tooltip("上传文件").classes("text-caption")
                send_btn = ui.button(icon="sym_r_send").props("color=emerald-800")
                with send_btn:
                    ui.tooltip("发送").classes("text-caption")

    # Keyboard event handler for the textarea
    # press 'enter' => send message, 'shift+enter' => newline.
    text_input.on(
        "keydown.enter",
        lambda: send_message(),
        js_handler="""
        (e) => {
            if (!e.shiftKey && !e.isComposing) {
                emit(e);
                e.preventDefault();
            }
        }""",
    )


    # --- Inner functions ---
    async def _init_message_container():
        app.storage.client["current_session_id"] = None
        app.storage.client["citations"] = {}
        app.storage.client["messages"] = {}
        message_container.clear()
        message_container.classes(remove="flex-grow overflow-y-auto")
        with message_container:
            ui.markdown("### 你想了解什么？").classes("text-center text-gray-900 mt-48")


    # --- Callbacks & Event Handlers ---

    # 1. User manager, login, logout, change password, etc.
    async def user_manager_clicked():
        user_manager(app, client_events)

    async def user_logged_in_handler():
        from .services import load_sessions_by_user
        from .viewers import show_session_history

        top_sessions = await load_sessions_by_user(
            app.storage.user["current_user"]["id"],
            limit=100,
        )
        show_session_history(top_sessions, session_history_col, client_events)
        await _init_message_container()

    client_events.user_logged_in.subscribe(user_logged_in_handler)
    user_manager_lbl.on("click", user_manager_clicked)
    user_manager_lbl.bind_text_from(
        app.storage.user,
        "current_user",
        backward=lambda u: (
            f"{u['username']} ({u['account']})" if u and u["account"] else "访客"
        ),
    )


    # 2. ...


    async def send_message(message: str | None = None):
        ...


    # --- Login and Initialize UI data ---
    if (
        "current_user" not in app.storage.user
        or app.storage.user["current_user"].get("id") is None
    ):
        app.storage.user["current_user"] = User().model_dump()
        client_events.user_logged_in.emit(app.storage.user["current_user"]["account"])
        logger.info("No saved user, go on as Guest.")
    else:
        try:
            user = await login(app.storage.user["current_user"]["account"], None)
            app.storage.user["current_user"] = user.model_dump()
            logger.info(f"User {user.username}({user.account}) logged in.")
        except SSOUnavailableError:
            app.storage.user["current_user"] = User().model_dump()
            ui.notify("SSO 服务不可用，以访客身份登录。", type="negative")
            logger.info("SSO Service unavailable, forced to longin as Guest.")
        except AccountNotExistsError:
            app.storage.user["current_user"] = User().model_dump()
            ui.notify("用户账户不存在，改以访客身份登录。", type="negative")
            logger.info("Saved user is invalid, resetting to Guest.")
        except Exception as e:
            app.storage.user["current_user"] = User().model_dump()
            ui.notify("登录错误，以访客身份登录")
            logger.info(f"Saved user login failed, resetting to Guest: {e!r}")

        client_events.user_logged_in.emit(app.storage.user["current_user"]["account"])

    # cached citations, {id: citation, ...}
    if "cached_citations" not in app.storage.general:
        # {id: Citation.model_dump(), ...}
        app.storage.general["cached_citations"] = {}

    # current session and its citation id set
    app.storage.client["current_session_id"] = None
    app.storage.client["citations"] = {}  # {msg_id: [citation_id, ...], ...}
    app.storage.client["messages"] = {}  # {msg_id: Message.model_dump(), ...}


if __name__ in {"__main__", "__mp_main__"}:
    start()
