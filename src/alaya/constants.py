MAIN_PAGE_STYLES = '''
/* For Webkit-based browsers (Chrome, Edge, Safari) */
::-webkit-scrollbar {
    width: 8px;  /* Width of the vertical scrollbar */
    height: 8px; /* Height of the horizontal scrollbar */
}

::-webkit-scrollbar-track {
    background: transparent; /* Make the track invisible */
}

::-webkit-scrollbar-thumb {
    background-color: #d1d5db; /* Light gray like gray-300 */
    border-radius: 10px;      /* Rounded corners for the thumb */
    border: 2px solid transparent; /* Padding around the thumb */
    background-clip: content-box;
}

::-webkit-scrollbar-thumb:hover {
    background-color: #9ca3af; /* Darker gray , like gray-400 */
}

/* For Firefox */
* {
    scrollbar-width: thin;
    scrollbar-color: #d1d5db transparent; /* thumb and track color */
}

/* Markdown width/overflow constraints */
.chat-md {
    width: 100%;
    max-width: 100%;
    overflow-x: hidden;
    overflow-wrap: anywhere;
}
.chat-md :where(img, svg, video, iframe, canvas) {
    max-width: 100%;
    height: auto;
}
.chat-md :where(pre) { max-width: 100%; overflow-x: auto; white-space: pre; }
.chat-md :where(code) { white-space: pre; }
.chat-md :where(table) {
    display: block;
    width: 100%;
    max-width: 100%;
    table-layout: fixed;
    overflow-x: auto;       /* table scrolls inside markdown, not container */
}
.chat-md :where(th, td) { word-break: break-word; }

/* Ensure the chat column never gets a horizontal scrollbar */
.chat-scroll { overflow-x: hidden; overflow-y: scroll; }

.nicegui-markdown h1 { font-size: 28px; font-weight: 600; }
.nicegui-markdown h2 { font-size: 26px; font-weight: 600; }
.nicegui-markdown h3 { font-size: 24px; font-weight: 600; }
.nicegui-markdown h4 { font-size: 22px; font-weight: 600; }
.nicegui-markdown h5 { font-size: 20px; font-weight: 600; }
.nicegui-markdown h6 { font-size: 18px; font-weight: 600; }
'''

SCROLL_TO_BOTTOM_JS = """
(() => {
    const el = document.getElementById('scrollable-card');
    if (!el) return false;
    return el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
})()
"""

INIT_RSS_SCRIPTS = [
    "DROP TABLE IF EXISTS query_segments",
    "DROP TABLE IF EXISTS session_messages",
    "DROP TABLE IF EXISTS sessions",
    "DROP TABLE IF EXISTS users",
    """
    CREATE TABLE users (
        id UUID PRIMARY KEY,
        account VARCHAR(20) UNIQUE NOT NULL,
        username VARCHAR(50) NOT NULL,
        user_path VARCHAR(100) NOT NULL,
        summary TEXT DEFAULT NULL,
        summary_time TIMESTAMP(6) DEFAULT NULL,
        INDEX idx_account (account),
        INDEX idx_summary_time (summary_time)
    );""",
    """
    CREATE TABLE sessions (
        id UUID PRIMARY KEY,
        title VARCHAR(100) NOT NULL,
        created_ts TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
        user_id UUID NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_title (title),
        INDEX idx_ts (created_ts)
    );""",
    """
    CREATE TABLE session_messages (
        id UUID PRIMARY KEY,
        session_id UUID NOT NULL,
        seq_no INT NOT NULL,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        created_ts TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
        likes INT NOT NULL DEFAULT 0,
        dislikes INT NOT NULL DEFAULT 0,
        pair_id UUID NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        INDEX idx_session (session_id),
        INDEX idx_ts (created_ts)
    );""",
    """
    CREATE TABLE query_segments (
        query_id UUID NOT NULL,
        segment_id UUID NOT NULL,
        seq_no INT NOT NULL,
        PRIMARY KEY (query_id, segment_id),
        FOREIGN KEY (query_id) REFERENCES session_messages(id) ON DELETE CASCADE
    );""",
]
