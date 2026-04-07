from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..events import ClientEvents

from ..models import Session, Message
from .chat_viewer import (
    display_bot_message,
    display_user_message,
    display_message_footer,
    scroll_to_bottom,
)

from nicegui import ui


def show_session_history(
    sessions: list[Session], container: ui.column, events: ClientEvents
) -> None:
    """
    Show session history in the given container.

    Arguments:
        sessions: A list of Session objects to display.
        container: The UI container where session history will be displayed.
    """
    container.clear()
    if not sessions:
        return

    with container:
        for session in sessions:
            with ui.row().classes(
                "w-full items-center no-wrap rounded-lg py-2 pr-2 hover:bg-neutral-200"
            ):
                # 1. Main button(link) for loading session
                with (
                    ui.label(session.title)
                    .classes(
                        "flex-grow min-w-0 rounded-lg pl-2 cursor-pointer "
                        "text-ellipsis no-underline text-gray-600 "
                        "whitespace-nowrap overflow-hidden text-body2 "
                    )
                    .on(
                        "click",
                        lambda _, sid=session.id: events.history_session_clicked.emit(
                            sid
                        ),
                    )
                ):
                    ui.tooltip(session.title).classes("text-caption")
                # 2. More options button with a context menu
                with (
                    ui.button(icon="sym_o_more_horiz")
                    .props("flat size=sm round dense color=gray-600")
                    .classes("opacity-0 hover:opacity-100 transition-opacity")
                ):
                    with ui.menu().classes("text-gray-700"):
                        with ui.menu_item(
                            on_click=lambda _, i=session.id: (
                                events.edit_session_title_clicked.emit(i)
                            ),
                        ):
                            with ui.row().classes("items-center"):
                                ui.icon("sym_o_edit").props("color=gray-700 size=20px")
                                ui.label("修改标题")
                        with ui.menu_item(
                            on_click=lambda _, i=session.id: (
                                events.pin_session_clicked.emit(i)
                            )
                        ):
                            with ui.row().classes("items-center"):
                                ui.icon("sym_o_push_pin").props(
                                    "color=gray-700 size=20px"
                                )
                                ui.label("置顶")
                        with ui.menu_item(
                            on_click=lambda _, i=session.id: (
                                events.delete_session_clicked.emit(i)
                            )
                        ):
                            with ui.row().classes("items-center"):
                                ui.icon("sym_o_delete").props("size=20px").classes(
                                    "text-red-500"
                                )
                                ui.label("删除").classes("text-red-500")


async def join_history_session(
    session_id: str, container: ui.column, username: str, events: ClientEvents
) -> tuple[dict[str, list[str]], list[Message]]:
    """
    Join a history session, display its messages in the given container, and
    return associated citation IDs for the session, organized by query ID.

    Arguments:
        session_id: The ID of the session to join.
        container: The UI container where session messages will be displayed.
        username: The username of the current user.

    Returns:
        A tuple containing:
            - A dictionary mapping query IDs to lists of citation IDs.
            - A list of Message objects in the session.
    """
    from ..services import load_messages_by_session, load_citation_ids_by_session

    container.clear()
    container.classes(add="flex-grow overflow-y-auto")
    messages = await load_messages_by_session(session_id)

    with container:
        for message in messages:
            if message.role == "user":
                await display_user_message(
                    message.content,
                    username,
                    message.created_ts,
                )
            else:
                await display_bot_message(message.content)
                await display_message_footer(
                    message.id,
                    message.pair_id,
                    events,
                    message.created_ts,
                    message.likes,
                    message.dislikes,
                )

    await scroll_to_bottom(container)

    return await load_citation_ids_by_session(session_id), messages


async def session_browser(user_id: str, events: ClientEvents):
    """
    Browse sessions for a given user.

    Arguments:
        user_id: The ID of the user.

    Returns:
        None
    """
    if not user_id:
        return

    from ..services import next_session_batch, search_result_batch
    from ..constants import SCROLL_TO_BOTTOM_JS
    from ..fts import search_sessions, build_index_for_user
    import asyncio

    retriever = None
    session_ids = None
    indexing_task = None

    async def _init_index():
        nonlocal retriever, session_ids
        retriever, session_ids = await build_index_for_user(user_id)

    # Start indexing in the background immediately
    indexing_task = asyncio.create_task(_init_index())

    last_session_id = None

    # session_brief_batch as: [(id, title, user_id, created_ts, content), ...]
    async def check():
        nonlocal last_session_id
        try:
            if await ui.run_javascript(SCROLL_TO_BOTTOM_JS):
                batch = await next_session_batch(user_id, last_session_id, 10)
                if batch:
                    last_session_id = batch[-1][0]
                    with browser_card:
                        await show_batch(batch)
                else:
                    tmr.deactivate()
                    with browser_card:
                        ui.label("没有更多对话了").classes(
                            "mx-auto text-gray-500 py-4 text-caption"
                        )
        except TimeoutError:
            pass  # client might have disconnected

    async def show_batch(batch: list[tuple]):
        with browser_card:
            for s in batch:
                with (
                    ui.column()
                    .classes(
                        "w-full hover:bg-gray-100 cursor-pointer rounded-lg gap-0 p-2"
                    )
                    .on(
                        "click",
                        lambda _, sid=s[0]: session_clicked_callback(sid),
                    )
                ):
                    with ui.row().classes("justify-between items-center"):
                        ui.label(s[1]).classes("p-2 font-semibold")
                        ui.label(s[3].strftime("%Y-%m-%d %H:%M")).classes(
                            "text-gray-500 text-caption p-2"
                        )
                    ui.label(s[4]).classes(
                        "py-0 px-2 text-gray-600 text-body2 overflow-hidden "
                        "line-clamp-2"
                    )

    with (
        ui.dialog() as s_dialog,
        ui.card().classes("w-5xl max-w-full h-3/4 overflow-hidden gap-0 py-8"),
    ):
        with ui.row().classes("w-full item-center"):
            search_inp = (
                ui.input(
                    label=None,
                    placeholder="全文模糊搜索最相符的对话...",
                )
                .classes("flex-1 px-2 shadow-none")
                .props("rounded outlined dense color=green-10")
            )
            with search_inp:
                _ = (
                    ui.button(
                        color="grey-6",
                        # icon="sym_r_delete",
                        icon="cancel",
                        on_click=lambda _: clear_clicked_callback(),
                    )
                    .props("flat dense")
                    .bind_visibility_from(search_inp, "value")
                )
                _ = (
                    ui.button(
                        color="green-10",
                        icon="sym_r_search",
                        on_click=lambda _: search_clicked_callback(),
                    )
                    .props("flat dense")
                    .bind_visibility_from(search_inp, "value")
                )
            search_inp.on(
                "keydown.enter",
                lambda: search_clicked_callback(),
                js_handler="""
                (e) => {
                    if (!e.shiftKey && !e.isComposing) {
                        emit(e);
                        e.preventDefault();
                    }
                }""",
            )

        browser_card = (
            ui.card()
            .classes(
                "w-full h-full overflow-x-hidden overflow-y-scroll shadow-none pl-0"
            )
            .props('id="scrollable-card"')
        )

    s_dialog.open()
    tmr = ui.timer(0.1, check)

    async def session_clicked_callback(session_id: str):
        s_dialog.close()
        tmr.deactivate()
        events.history_session_clicked.emit(session_id)

    async def search_clicked_callback():
        keyword = search_inp.value.strip()
        if not keyword:
            return
        nonlocal retriever, session_ids, indexing_task

        tmr.deactivate()
        browser_card.clear()
        search_inp.disable()
        with browser_card:
            ui.label("搜索中，请稍候...").classes(
                "mx-auto text-gray-500 py-4 text-caption"
            )
        await asyncio.sleep(0.05)  # allow UI to update

        if indexing_task and not indexing_task.done():
            # Wait for the background indexing to complete if not already done
            await indexing_task

        # Fallback just in case, though task should have populated them
        if retriever is None or session_ids is None:
            retriever, session_ids = await build_index_for_user(user_id)

        results = search_sessions(
            retriever, session_ids, keyword, top_k=len(session_ids)
        )
        browser_card.clear()
        with browser_card:
            if not results:
                ui.label("-- 未找到相关对话 --").classes(
                    "mx-auto text-gray-500 pt-4 text-caption"
                )
            else:
                ui.label(f"-- 找到 {len(results)} 条结果 --").classes(
                    "mx-auto text-gray-500 pt-4 text-caption"
                )
        await show_batch(await search_result_batch(results))
        search_inp.enable()

    async def clear_clicked_callback():
        nonlocal last_session_id
        search_inp.set_value(None)
        last_session_id = None
        browser_card.clear()
        tmr.activate()
