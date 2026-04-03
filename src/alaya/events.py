from nicegui import Event
from nicegui.events import ClickEventArguments
from dataclasses import dataclass, field


@dataclass
class ClientEvents:
    # --- Common Events ---
    user_logged_in: Event = field(default_factory=lambda: Event[str]())

    # --- Session Viewer Events ---
    history_session_clicked: Event = field(default_factory=lambda: Event[str]())
    delete_session_clicked: Event = field(default_factory=lambda: Event[str]())
    pin_session_clicked: Event = field(default_factory=lambda: Event[str]())
    edit_session_title_clicked: Event = field(default_factory=lambda: Event[str]())

    # --- Chat Viewer Events ---
    copy_response_clicked: Event = field(default_factory=lambda: Event[str]())
    regenerate_response_clicked: Event = field(default_factory=lambda: Event[str]())
    like_response_clicked: Event = field(
        default_factory=lambda: Event[ClickEventArguments, str]()
    )
    dislike_response_clicked: Event = field(
        default_factory=lambda: Event[ClickEventArguments, str]()
    )
    download_response_clicked: Event = field(default_factory=lambda: Event[str]())
    show_message_citations_clicked: Event = field(default_factory=lambda: Event[str]())
