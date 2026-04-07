from typing import Sequence
from ..models import Citation


async def load_citations_by_ids(
    citation_ids: Sequence[str] | set[str],
    cached_citations: dict[str, dict],
    user_path: str,
) -> list[Citation]:
    """Load citations by their IDs from cached citations or HuRAG API.

    Args:
        citation_ids (Sequence|set): Citation IDs to load.
        cached_citations (dict): Dictionary of cached citations.

    Returns:
        list[Citation]: List of loaded Citation objects.
    """
    ids = set(citation_ids)
    uncached_ids = ids - cached_citations.keys()
    cached_ids = ids & cached_citations.keys()
    # Load cached citations
    citations = [Citation.model_validate(cached_citations[cid]) for cid in cached_ids]
    if not uncached_ids:
        return citations

    # Load uncached citations from HuRAG SDK
    from ...knowledge_base import get_knowledge_by_segment_ids

    kns = await get_knowledge_by_segment_ids(list(uncached_ids), user_path)
    for knowledge in kns:
        citation = Citation.from_knowledge(knowledge)
        citations.append(citation)
        # Update cached citations
        cached_citations[citation.id] = citation.model_dump()

    return citations
