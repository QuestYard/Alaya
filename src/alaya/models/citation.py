import re
from pydantic import BaseModel
from typing import Self


class Citation(BaseModel):
    id: str
    doc_id: str
    doc: str
    content: str

    def __repr__(self):
        return f"Citation(id='{self.id}', doc='{self.doc}', content='{
            ' '.join(self.content.split('\n'))[:40]
        }')"

    @classmethod
    def from_knowledge(cls, knowledge: dict) -> Self:
        ct = cls(
            id=knowledge["segment_id"] or "",
            doc_id=knowledge["metadata"]["id"] or "",
            doc=knowledge["metadata"]["title"] or "",
            content=knowledge["content"] or "",
        )
        return ct

    @property
    def text(self) -> str:
        """Cleaned content to show in web pages"""
        return sanitize_markdown(self.content)

    @property
    def brief(self) -> str:
        """Cleaned first 100 chars of contents"""
        if len(self.content) > 100:
            return sanitize_markdown(self.content[:100] + "...")
        else:
            return sanitize_markdown(self.content)


# --- Utility functions ---

_CJK = r"\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af"


def sanitize_markdown(content: str) -> str:
    """Sanitize markdown content to present clean format to show in UI.

    1. Remove excessive blank lines (more than 2 consecutive newlines).
    2. Change HTML tags to `[]` wrapping.
    3. Remove heading marks and underline the heads instead.
    4. Insert spaces around inline LaTeX expressions.
    5. Remove leading and trailing whitespace.

    Args:
        content (str): The markdown content to sanitize.

    Returns:
        str: The sanitized markdown content.
    """

    def _replace_tag_brackets(text: str) -> str:
        text = re.sub(r"<(\w+)([^>]*)/>", r"[\1\2/]", text)  # self-closing tags
        text = re.sub(
            r"<(\w+)([^>]*)>(.*?)</\1>",
            lambda m: (
                f"[{m.group(1)}{m.group(2)}]{_replace_tag_brackets(m.group(3))}[/{
                    m.group(1)
                }]"
            ),
            text,
            flags=re.DOTALL,
        )
        return text

    # 1. Remove excessive blank lines (more than 2 consecutive newlines)
    content = re.sub(r"\n{3,}", "\n\n", content)
    # 2. Change HTML tags to `[]` wrapping
    content = _replace_tag_brackets(content)
    # 3. Remove heading marks and underline the heads instead
    content = re.sub(
        r"^(#{1,})\s*(.+)$",
        lambda m: f"<u>{m.group(2)}</u>",
        content,
        flags=re.MULTILINE,
    )
    # 4. Insert spaces around inline LaTeX expressions
    content = re.sub(rf"([{_CJK}A-Za-z0-9])(\$[^$]+\$)", r"\1 \2", content)
    content = re.sub(rf"(\$[^$]+\$)([{_CJK}A-Za-z0-9])", r"\1 \2", content)
    # 5. Remove leading and trailing whitespace and return the content
    return content.strip()
