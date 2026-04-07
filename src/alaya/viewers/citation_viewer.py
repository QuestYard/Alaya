from nicegui import ui
from typing import Sequence

from ..services import load_citations_by_ids


async def show_citations(
    cached_citations: dict[str, dict],
    ids: Sequence[str] | set[str],
    user_path: str,
    ui_card: ui.card,
    ui_spinner: ui.spinner,
):
    """Show citations in the UI card for the given citation IDs.

    Args:
        cached_citations (dict): Citations cached in `ui.storage.general`.
        ids (Sequence | set): The segment IDs to show citations for.
        user_path (str): The user path for API requests.
        ui_card (ui.Card): The UI card to which the citations will be shown.
        ui_spinner (ui.Spinner): The UI spinner to indicate loading state.

    Returns:
        None
    """
    ui_card.clear()

    if not ids:
        ui.notify("没有引用的知识段。", type="warning")
        return

    ui_spinner.set_visibility(True)
    import asyncio

    await asyncio.sleep(0.05)  # allow UI to update
    citations = await load_citations_by_ids(
        ids,
        cached_citations,
        user_path,
    )
    ui_spinner.set_visibility(False)
    ui.notify(f"已加载 {len(citations)} 条引文。", type="positive")
    if isinstance(ids, set):
        # reorder citations by doc_id and citation id
        citations.sort(key=lambda c: f"{c.doc_id}_{c.id}")
    else:
        # keep elements in citations in the same order as ids
        id_to_citation = {c.id: c for c in citations}
        citations = [id_to_citation[cid] for cid in ids if cid in id_to_citation]

    with ui_card:
        for i, ct in enumerate(citations):
            with (
                ui.column(wrap=True)
                .classes(
                    "w-full p-2 gap-2 border-b border-gray-300 "
                    "hover:bg-zinc-100 cursor-zoom-in"
                )
                .on("click", lambda _, t=ct.doc, c=ct.content: _on_citation_click(t, c))
            ):
                ui.tooltip("查看全文...").classes("text-caption")
                ui.label(f"{i + 1}.{ct.doc}").classes("text-body2 font-semibold")
                ui.markdown(
                    ct.brief,
                    extras=["fenced-code-blocks", "tables", "latex", "mermaid"],
                ).classes("text-body2 text-gray-700")


# --- Event handlers ---


def _on_citation_click(title, content):
    """Show full content, without any format cleaning."""
    with ui.dialog() as dialog, ui.card().classes("p-4 w-3xl max-w-full gap-0"):
        ui.label(title).classes("text-subtitle1 font-bold text-center w-full")
        with ui.tabs() as tabs:
            text_tab = ui.tab("文本")
            markdown_tab = ui.tab("MARKDOWN")
        with ui.tab_panels(tabs, value=text_tab).classes("w-full"):
            with ui.tab_panel(text_tab):
                ui.label(content).classes(
                    "whitespace-pre-wrap text-body2 mt-2 max-h-[60vh] "
                    "text-left text-gray-700 w-full overflow-y-auto"
                )
            with ui.tab_panel(markdown_tab):
                ui.markdown(content).classes(
                    "whitespace-pre-wrap text-body2 mt-2 max-h-[60vh] "
                    "text-left text-gray-700 w-full overflow-y-auto"
                )
    dialog.open()
