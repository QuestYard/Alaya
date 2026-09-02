from nicegui import ui
from datetime import datetime
from ..events import ClientEvents


async def display_user_message(
    message: str,
    username: str,
    timestamp: datetime = datetime.now(),
) -> ui.chat_message:
    """Display a user message in the chat viewer."""
    return ui.chat_message(
        message, name=username, stamp=timestamp.strftime("%Y-%m-%d %H:%M"), sent=True
    )


async def display_bot_message(content) -> ui.markdown:
    """Display a bot message in the chat viewer."""
    import mdformat

    return ui.markdown(
        mdformat.text(content) if content else "",
        extras=["fenced-code-blocks", "tables", "latex", "mermaid"],
    ).classes("w-full max-w-full text-gray-800")


async def display_message_footer(
    message_id: str | None,
    pair_id: str | None,
    events: ClientEvents,
    timestamp: datetime = datetime.now(),
    likes: int = 0,
    dislikes: int = 0,
) -> ui.column:
    """Display a footer for a message with actions like 'like' and 'dislike'."""
    footer_col = ui.column().classes("w-full self-stretch items-stretch gap-0")
    with footer_col:
        ui.markdown(
            f"---\n*以上内容为人工智能生成，仅供参考。*"
            f" {timestamp.strftime('%Y-%m-%d %H:%M')}",
        ).classes("text-caption text-gray-500 mb-0")
        if message_id and pair_id:
            with ui.row().classes("justify-left py-0 my-0"):
                with ui.button(
                    on_click=lambda _, i=message_id: events.copy_response_clicked.emit(
                        i
                    ),
                    icon="sym_r_content_copy",
                ).props("round dense flat size=sm color=gray-500 my-0 py-0"):
                    ui.tooltip("Copy").classes("text-caption")

                with ui.button(
                    on_click=lambda _, i=pair_id: (
                        events.regenerate_response_clicked.emit(i)
                    ),
                    icon="sym_r_refresh",
                ).props("round dense flat size=sm color=gray-500 my-0 py-0"):
                    ui.tooltip("Regenerate").classes("text-caption")

                with ui.button(
                    on_click=lambda e, i=message_id: events.like_response_clicked.emit(
                        e, i
                    ),
                    icon="sym_r_thumb_up",
                ).props(
                    "round dense flat size=sm color=gray-500 my-0 py-0"
                    if not likes
                    else "round dense flat size=sm color=amber-600 my-0 py-0"
                ):
                    ui.tooltip("Like").classes("text-caption")

                with ui.button(
                    on_click=lambda e, i=message_id: (
                        events.dislike_response_clicked.emit(e, i)
                    ),
                    icon="sym_r_thumb_down",
                ).props(
                    "round dense flat size=sm color=gray-500 my-0 py-0"
                    if not dislikes
                    else "round dense flat size=sm color=amber-600 my-0 py-0"
                ):
                    ui.tooltip("Dislike").classes("text-caption")

                with ui.button(
                    on_click=lambda _, i=message_id: (
                        events.download_response_clicked.emit(i)
                    ),
                    icon="sym_r_download",
                ).props("round dense flat size=sm color=gray-500 my-0 py-0"):
                    ui.tooltip("Download").classes("text-caption")

                # with ui.button(
                #     on_click=(
                #         lambda _, i=message_id: (
                #             events.show_message_citations_clicked.emit(i)
                #         )
                #     ),
                #     icon="sym_r_auto_stories",
                # ).props("round dense flat size=sm color=gray-500 my-0 py-0"):
                #     ui.tooltip("Citations").classes("text-caption")

    return footer_col


async def scroll_to_bottom(c):
    ui.run_javascript(
        f"getElement({c.id}).scrollTop = getElement({c.id}).scrollHeight;"
    )
