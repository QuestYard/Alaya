import os
from dotenv import load_dotenv

load_dotenv()

if os.getenv("DEEPSEEK_API_KEY", None) is None:
    raise ValueError("Environment Vairable 'DEEPSEEK_API_KEY' not found.")


from .alaya_agent import (
    get_agent,
    AgentDeps,
    EvidenceType,
    SearchQuality,
)
from .history_manager import (
    compress_history_if_needed,
    estimate_tokens,
    get_context_limit,
    ContextSize,
)


__all__ = [
    "get_agent",
    "AgentDeps",
    "EvidenceType",
    "SearchQuality",
    "compress_history_if_needed",
    "estimate_tokens",
    "get_context_limit",
    "ContextSize",
]
