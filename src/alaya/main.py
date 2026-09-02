import os
import asyncio
import mdformat

from nicegui import ui, app
from fastapi.staticfiles import StaticFiles

from . import logger, conf
from .events import ClientEvents
from .constants import MAIN_PAGE_STYLES
from .models import User, Message
from .services import login, SSOUnavailableError, AccountNotExistsError
from .viewers import user_manager, scroll_to_bottom


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

#         # 2. Citation Button and Badge (not be used by now, reserved)
#         with ui.row().classes("items-center gap-2"):
#             citation_btn = ui.button(icon="sym_r_book").props(
#                 "fab-mini flat color=gray-800"
#             )
#             with citation_btn:
#                 citations_badge = ui.badge(color="red-700", text_color="white").classes(
#                     "pointer-events-none absolute top-1 right-1 "
#                     "translate-x-1/3 -translate-y-1/3 "
#                     "min-w-[16px] h-[16px] px-[4px] py-0 "
#                     "flex items-center justify-center "
#                     "rounded-full text-[10px] leading-none shadow"
#                 )
#                 ui.tooltip("隐藏引文").classes("text-caption")

        # 2. Toggle button to open/close the thinking part drawer
        with ui.row().classes("items-center gap-2"):
            thinking_btn = ui.button("THINKING", icon="sym_r_cognition").props(
                "fab-mini flat color=gray-800"
            )
            with thinking_btn:
                ui.tooltip("显示/隐藏思考内容").classes("text-caption")

#     # --- Right drawer (not be used by now, reserved) ---
#     citation_drawer = (
#         ui.right_drawer(fixed=False, value=False)
#         .props("width=420")
#         .classes("border-l-1 border-gray-300")
#     )
#     with citation_drawer, ui.column().classes("fit no-wrap"):
#         # 1. Drawer Title
#         with ui.row().classes("w-full items-center"):
#             ui.label("知识库引文").classes("text-subtitle1 font-bold")
#             citation_spinner = ui.spinner("dots", color="zinc-500", size="sm")
#             citation_spinner.set_visibility(False)
#         # 2. Citations Card (to be filled dynamically)
#         citations_card = (
#             ui.card()
#             .classes(
#                 "shadow-none border-0 w-full flex-grow overflow-y-auto mb-2 pl-0 pt-0"
#             )
#             .style(
#                 "mask-image: linear-gradient(to bottom, transparent, "
#                 "black 20px, black 90%, transparent);"
#                 "-webkit-mask-image: linear-gradient(to bottom, transparent, "
#                 "black 20px, black 90%, transparent);"
#             )
#         )

    # --- Right drawer (not be used by now, reserved) ---
    thinking_drawer = (
        ui.right_drawer(fixed=False, value=False)
        .props("width=420")
        .classes("border-l-1 border-gray-300")
    )
    with thinking_drawer, ui.column().classes("fit no-wrap"):
#         thinking_card = (
#             ui.card()
#             .classes(
#                 "shadow-none border-0 w-full flex-grow overflow-y-auto mb-2 pl-0 pt-0"
#             )
#             .style(
#                 "mask-image: linear-gradient(to bottom, transparent, "
#                 "black 20px, black 90%, transparent);"
#                 "-webkit-mask-image: linear-gradient(to bottom, transparent, "
#                 "black 20px, black 90%, transparent);"
#             )
#         )
#         with thinking_card:
        thinking_card = ui.markdown("").classes("text-body2 text-gray-500 italic")


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
    async def toggle_thinking_drawer():
        thinking_drawer.value = not thinking_drawer.value

    async def show_thinking_drawer():
        thinking_drawer.value = True

    async def hide_thinking_drawer():
        thinking_drawer.value = False

    async def clear_thinking_card():
        thinking_card.set_content("")

    async def show_thinking_part(text: str, stream: bool = True):
        if stream:
            thinking_card.set_content(thinking_card.content + text)
        else:
            thinking_card.set_content(text)

    async def _init_message_container():
        app.storage.client["current_session_id"] = None
        app.storage.client["messages"] = {}
        app.storage.client["raw_msgs"] = []
        message_container.clear()
        message_container.classes(remove="flex-grow overflow-y-auto")
        with message_container:
            ui.markdown("### 你想了解什么？").classes("text-center text-gray-900 mt-48")
        await clear_thinking_card()
        await hide_thinking_drawer()


    # --- Callbacks & Event Handlers ---

    # 1. User management: login, logout, change password, etc.
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

#     # 2. Citation management (not be used by now, reserved)
#     async def toggle_citation_drawer():
#         if citation_drawer.value:
#             citation_drawer.value = False
# 
#     citation_btn.on_click(lambda: toggle_citation_drawer())
#     citation_btn.bind_icon_from(
#         citation_drawer,
#         "value",
#         backward=lambda o: "sym_r_auto_stories" if o else "sym_r_book",
#     )
#     citations_badge.bind_visibility_from(
#         citation_drawer,
#         "value",
#     )

    # 2. Thinking drawer management
    thinking_btn.on_click(lambda: toggle_thinking_drawer())

    # 3. Session management
    async def new_session_clicked():
        if app.storage.client["current_session_id"] is None:
            return  # already in a new session
        await _init_message_container()

    new_session_btn.on_click(new_session_clicked)

    async def search_session_clicked():
        from .viewers import session_browser

        await session_browser(app.storage.user["current_user"]["id"], client_events)

    search_session_btn.on_click(search_session_clicked)

    async def history_session_clicked_handler(session_id: str):
        from .viewers import join_history_session
        from .agents import restore_message_history

        app.storage.client["current_session_id"] = session_id
        _, msgs = await join_history_session(
            session_id,
            message_container,
            app.storage.user["current_user"]["username"],
            client_events,
        )
        app.storage.client["messages"] = {m.id: m.model_dump() for m in msgs}
        app.storage.client["raw_msgs"] = restore_message_history(msgs)
        await clear_thinking_card()
        await hide_thinking_drawer()
        await scroll_to_bottom(message_container)

    client_events.history_session_clicked.subscribe(history_session_clicked_handler)

    async def edit_session_title_clicked_handler(session_id: str):
        from .services import (
            load_session_by_id,
            update_session_title,
            load_sessions_by_user,
        )
        from .viewers import show_session_history

        session = await load_session_by_id(session_id)
        if not session:
            return

        with ui.dialog() as dialog, ui.card().classes("w-2xl p-4"):
            new_ttl = ui.input(
                label="修改会话标题(最多20字)",
                value=session.title,
                placeholder="新标题",
            ).classes("w-full mx-auto")
            with ui.row().classes("w-full justify-end"):
                ui.button(
                    "确定",
                    color="emerald-800",
                    on_click=lambda: dialog.submit((new_ttl.value or "").strip()[:20]),
                ).props("flat").classes("text-white px-6").bind_enabled_from(
                    new_ttl, "value"
                )
                ui.button(
                    "取消", color="zinc-200", on_click=lambda: dialog.submit(None)
                ).props("flat").classes("text-gray-600 px-6")
        result = await dialog
        if not result:
            return  # cancelled
        await update_session_title(session_id, result)
        top_sessions = await load_sessions_by_user(
            app.storage.user["current_user"]["id"],
            limit=100,
        )
        show_session_history(top_sessions, session_history_col, client_events)

    client_events.edit_session_title_clicked.subscribe(
        edit_session_title_clicked_handler
    )

    async def delete_session_clicked_handler(session_id: str):
        from .services import delete_session_by_id, load_sessions_by_user
        from .viewers import show_session_history

        with ui.dialog() as dialog, ui.card().classes("w-96 pt-6 gap-0"):
            ui.label("确认删除该会话？此操作不可撤销。").classes("text-base mx-auto")
            with ui.row().classes("w-full justify-center mt-4"):
                ui.button(
                    "删除", color="emerald-800", on_click=lambda: dialog.submit(True)
                ).props("flat").classes("text-white px-6")
                ui.button(
                    "取消", color="zinc-200", on_click=lambda: dialog.submit(False)
                ).props("flat").classes("text-gray-600 px-6")
        confirm = await dialog
        if confirm:
            await delete_session_by_id(session_id)
            ui.notify("会话已删除", type="positive")
            # Refresh session history
            top_sessions = await load_sessions_by_user(
                app.storage.user["current_user"]["id"], limit=100
            )
            show_session_history(top_sessions, session_history_col, client_events)
            # If deleted session is current, init message container
            if app.storage.client["current_session_id"] == session_id:
                await _init_message_container()

    client_events.delete_session_clicked.subscribe(delete_session_clicked_handler)

    async def pin_session_clicked_handler(session_id: str):
        from .services import pin_session_by_id, load_sessions_by_user
        from .viewers import show_session_history

        await pin_session_by_id(session_id)
        top_sessions = await load_sessions_by_user(
            app.storage.user["current_user"]["id"], limit=100
        )
        show_session_history(top_sessions, session_history_col, client_events)

    client_events.pin_session_clicked.subscribe(pin_session_clicked_handler)

    # 4. Message buttons, like, dislike, download, etc.
    async def copy_response_clicked_handler(message_id: str):
        msg = app.storage.client["messages"].get(message_id)
        if msg:
            ui.clipboard.write(msg["content"])
            ui.notify("已复制到剪贴板")
        else:
            ui.notify("消息未找到，复制失败", type="negative")

    client_events.copy_response_clicked.subscribe(copy_response_clicked_handler)

    async def regenerate_response_clicked_handler(message_id: str | None):
        msg = app.storage.client["messages"].get(message_id)
        await send_message(msg["content"])

    client_events.regenerate_response_clicked.subscribe(
        regenerate_response_clicked_handler
    )

    async def like_response_clicked_handler(e, message_id: str):
        from .services import like_message

        msg = app.storage.client["messages"].get(message_id)
        msg["likes"] = 1 - msg["likes"]
        e.sender.props("color=amber-600" if msg["likes"] else "color=gray-500")
        await like_message(msg["id"], msg["likes"])

    client_events.like_response_clicked.subscribe(like_response_clicked_handler)

    async def dislike_response_clicked_handler(e, message_id: str):
        from .services import dislike_message

        msg = app.storage.client["messages"].get(message_id)
        msg["dislikes"] = 1 - msg["dislikes"]
        e.sender.props("color=amber-600" if msg["dislikes"] else "color=gray-500")
        await dislike_message(msg["id"], msg["dislikes"])

    client_events.dislike_response_clicked.subscribe(dislike_response_clicked_handler)

    async def download_response_clicked_handler(message_id: str):
        msg = app.storage.client["messages"].get(message_id)
        if msg:
            filename = f"response_{message_id}.md"
            ui.download.content(msg["content"], filename)
        else:
            ui.notify("消息未找到，下载失败", type="negative")

    client_events.download_response_clicked.subscribe(download_response_clicked_handler)

    # 5. Others: UI, waiting spinner
    text_input.bind_enabled_from(waiting_spinner, "visible", backward=lambda v: not v)
    upload_btn.bind_enabled_from(waiting_spinner, "visible", backward=lambda v: not v)
    send_btn.bind_enabled_from(waiting_spinner, "visible", backward=lambda v: not v)

    # 6. Chating
    upload_btn.on_click(lambda: ui.notify("上传附件功能待实现"))

    async def send_message(message: str | None = None):
        from datetime import datetime
        from .utilities import generate_id
        from .viewers import (
            display_user_message,
            display_bot_message,
            display_message_footer,
            show_session_history,
        )
        from .services import (
            upsert_session,
            load_sessions_by_user,
            generate_session_title,
        )
        from . import hurag
        from .agents import (
            get_agent,
            AgentDeps,
            compress_history_if_needed,
        )
        from pydantic_ai.messages import (
            PartDeltaEvent,
            FunctionToolCallEvent,
            FunctionToolResultEvent,
            TextPartDelta,
            ThinkingPartDelta,
        )

        # Perpare user query and timestamp
        query = message or (text_input.value or "").strip()
        if not query:
            return
        query_ts = datetime.now()

        # Initialize session and message container if needed
        task = None
        if app.storage.client["current_session_id"] is None:
            # Generate new session's title in background
            task = asyncio.create_task(generate_session_title(query))
            app.storage.client["messages"] = {}
            app.storage.client["raw_msgs"] = []
            message_container.clear()
            message_container.classes(add="flex-grow overflow-y-auto")

        # Show user query
        with message_container:
            await display_user_message(
                query,
                app.storage.user["current_user"]["username"],
                query_ts,
            )
        text_input.set_value("")

        # Show waiting spinner and scroll to bottom, will disable input area
        waiting_spinner.set_visibility(True)
        await scroll_to_bottom(message_container)
        await show_thinking_drawer()

        # Agent loop and generate the final response
        agent = get_agent()
        http_client = await hurag.get_client()
        current_user = User.model_validate(app.storage.user["current_user"])
        deps = AgentDeps(user=current_user, client=http_client)

        app.storage.client["raw_msgs"], _ = compress_history_if_needed(
            app.storage.client["raw_msgs"]
        )

        response = ""
        with message_container:
            bot_msg_box = await display_bot_message(response)

            async with agent.run_stream_events(
                query,
                deps=deps,
                message_history=app.storage.client["raw_msgs"],
            ) as events:
                thinking_started = False

                async for event in events:
                    # 1. Tool call notification
                    if isinstance(event, FunctionToolCallEvent):
                        args_repr = str(event.part.args) if event.part.args else ""
                        if len(args_repr) > 120:
                            args_repr = args_repr[:117] + "..."
                        await show_thinking_part(
                            f"\n\n⚡ Tool Call: {event.part.tool_name}({args_repr})"
                        )
                    # 2. Tool completed notification (Suppress tool return value)
                    elif isinstance(event, FunctionToolResultEvent):
                        await show_thinking_part(
                            f"\n\n✔  Tool Completed: {event.part.tool_name}"
                        )
                    elif isinstance(event, PartDeltaEvent):
                        if isinstance(event.delta, ThinkingPartDelta):
                            if not thinking_started:
                                await show_thinking_part("\n\n🧠 Thinking: ")
                                thinking_started = True
                            await show_thinking_part(event.delta.content_delta or "")
                        elif isinstance(event.delta, TextPartDelta):
                            response += event.delta.content_delta
                            bot_msg_box.set_content(mdformat.text(response))
                            await scroll_to_bottom(message_container)

                app.storage.client["raw_msgs"] = events.all_messages()

        response_ts = datetime.now()

        # Save/Update session and messages
        if app.storage.user["current_user"]["id"] is not None:
            # Not a guest user
            if app.storage.client["current_session_id"] is None:
                # New session creation logic
                # 1) Wait and get the generated session title
                assert task is not None
                title = await task
                # 2) Save new session
                s, q, r = await upsert_session(
                    query=query,
                    query_ts=query_ts,
                    response=response,
                    response_ts=response_ts,
                    session_id=None,
                    title=title,
                    user_id=app.storage.user["current_user"]["id"],
                )
                # 3) Update current_session_id
                assert s is not None
                app.storage.client["current_session_id"] = s.id
            else:
                # Update existing session
                # 1) Update session
                _, q, r = await upsert_session(
                    query=query,
                    query_ts=query_ts,
                    response=response,
                    response_ts=response_ts,
                    session_id=app.storage.client["current_session_id"],
                )
            # Update current messages
            app.storage.client["messages"][q.id] = q.model_dump()
            app.storage.client["messages"][r.id] = r.model_dump()
            # Refresh recent sessions in the left drawer
            top_sessions = await load_sessions_by_user(
                app.storage.user["current_user"]["id"],
                limit=100,
            )
            show_session_history(top_sessions, session_history_col, client_events)
        else:
            # Guest user, no database saving, only temp storage
            temp_session_id = "guest_session"
            app.storage.client["current_session_id"] = temp_session_id
            qid = generate_id()
            rid = generate_id()
            q = Message(
                **{
                    "id": qid,
                    "session_id": temp_session_id,
                    "seq_no": len(app.storage.client["messages"]),
                    "role": "user",
                    "content": query,
                    "created_ts": query_ts,
                    "pair_id": rid,
                }
            )
            r = Message(
                **{
                    "id": rid,
                    "session_id": temp_session_id,
                    "seq_no": len(app.storage.client["messages"]) + 1,
                    "role": "assistant",
                    "content": response,
                    "created_ts": response_ts,
                    "pair_id": qid,
                }
            )
            app.storage.client["messages"][qid] = q.model_dump()
            app.storage.client["messages"][rid] = r.model_dump()

        # Add footbar to response message
        with message_container:
            await display_message_footer(
                app.storage.user["current_user"]["id"] and r.id,
                app.storage.user["current_user"]["id"] and q.id,
                client_events,
                response_ts,
            )

        # End of a round of event loop
        waiting_spinner.set_visibility(False)
        await scroll_to_bottom(message_container)
        text_input.run_method("focus")


        # --- End of send_message function ---

    send_btn.on_click(send_message)


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

    # current session ID and messages
    app.storage.client["current_session_id"] = None
    app.storage.client["messages"] = {}  # {msg_id: Message.model_dump(), ...}
    app.storage.client["raw_msgs"] = [] # list[ModelMessage]


if __name__ in {"__main__", "__mp_main__"}:
    start()
