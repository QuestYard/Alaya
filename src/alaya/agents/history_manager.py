"""Context window estimation and history compression for multi-turn conversations."""

from typing import Literal
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    ThinkingPart,
)

from .. import logger, conf

ContextSize = Literal["tiny", "medium", "large"]

# Token thresholds corresponding to context scale configurations:
# tiny: ~4K, medium: ~32K, large: ~256K
CONTEXT_LIMITS: dict[str, int] = {
    "tiny": conf.app.ctx_limit.tiny,
    "medium": conf.app.ctx_limit.medium,
    "large": conf.app.ctx_limit.large,
}

# Length of summaries of queries and answers
Q_SUMM_LEN: int = conf.app.summary_size.query
A_SUMM_LEN: int = conf.app.summary_size.answer


def estimate_tokens(messages: list[ModelMessage]) -> int:
    """
    Estimate the token usage of a list of ModelMessages.
    A conservative character-to-token ratio is used (avg ~1.8 chars/token for CJK).
    """
    total_chars = 0
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    total_chars += len(part.content)
                elif isinstance(part, ToolReturnPart):
                    content = str(part.content) if part.content is not None else ""
                    total_chars += len(content)
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart):
                    total_chars += len(part.content)
                elif isinstance(part, ThinkingPart):
                    total_chars += len(part.content)
                elif isinstance(part, ToolCallPart):
                    total_chars += len(part.tool_name) + len(str(part.args))

    return int(total_chars / 1.8) + 1


def get_context_limit() -> int:
    """Retrieve the maximum context tokens based on app configuration."""
    ctx_size = getattr(conf.app, "ctx_size", "large") or "large"
    return CONTEXT_LIMITS.get(str(ctx_size).lower(), CONTEXT_LIMITS["large"])


def compress_history_if_needed(
    messages: list[ModelMessage],
    *,
    keep_recent_turns: int = 2,
    compress_ratio_trigger: float = 0.85,
) -> tuple[list[ModelMessage], bool]:
    """
    Check if the current message history exceeds the context window threshold.
    If so, compress older turns into a concise summary while preserving
    recent turns intact.

    Args:
        messages: Complete list of ModelMessages.
        keep_recent_turns: Number of recent user-assistant turns to keep.
        compress_ratio_trigger: Trigger compression when estimated tokens
            exceed limit * ratio.

    Returns:
        (compressed_messages, was_compressed)
    """
    max_tokens = get_context_limit()
    current_tokens = estimate_tokens(messages)

    if current_tokens < int(max_tokens * compress_ratio_trigger):
        return messages, False

    # A conversation turn roughly consists of pairs of requests and responses.
    # We keep the last `keep_recent_turns * 2` messages intact.
    recent_count = keep_recent_turns * 2
    if len(messages) <= recent_count:
        return messages, False

    older_messages = messages[:-recent_count]
    recent_messages = messages[-recent_count:]

    # Extract user queries and assistant text responses from older messages
    summaries: list[str] = []
    current_user_query = ""
    current_assistant_reply = ""

    for msg in older_messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    if current_user_query and current_assistant_reply:
                        q_summary = current_user_query[:Q_SUMM_LEN]
                        a_summary = current_assistant_reply[:A_SUMM_LEN]
                        summaries.append(f"- 用户: {q_summary}\n  助手: {a_summary}")
                        current_assistant_reply = ""
                    current_user_query = part.content.strip()
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart):
                    current_assistant_reply += part.content.strip()

    if current_user_query and current_assistant_reply:
        q_summary = current_user_query[:Q_SUMM_LEN]
        a_summary = current_assistant_reply[:A_SUMM_LEN]
        summaries.append(f"- 用户: {q_summary}\n  助手: {a_summary}")

    if not summaries:
        return messages, False

    summary_text = "[历史会话摘要 / Compressed Previous Turns]:\n" + "\n".join(
        summaries
    )

    compressed_request = ModelRequest(parts=[UserPromptPart(content=summary_text)])
    compressed_response = ModelResponse(
        parts=[TextPart(content="已同步并记住以上历史会话背景要点，请继续提问。")]
    )

    new_history = [compressed_request, compressed_response] + list(recent_messages)
    logger.info(
        f"Message history compressed: {len(messages)} msgs "
        f"({current_tokens} est. tokens) -> {len(new_history)} msgs "
        f"({estimate_tokens(new_history)} est. tokens)"
    )

    return new_history, True
