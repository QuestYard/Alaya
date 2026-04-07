import pkuseg


_seg = None
_executor = None


def _get_seg():
    global _seg
    if _seg is None:
        _seg = pkuseg.pkuseg()
    return _seg


def cleanup(text: str) -> str:
    """
    Cleans the input text (naive version).
    More advanced cleaning can be implemented as needed.
    Must be called both before indexing and querying.
    """
    return text.strip().lower()


def tokenize(corpus: list[str]) -> list[list]:
    """
    Tokenize a list of texts using pkuseg for search mode.

    Args:
        corpus (list[str]): A list of texts to be tokenized.

    Returns:
        list[list[str]]: A list where each element is a list of tokens.
    """
    if not corpus:
        return []

    seg = _get_seg()
    return [seg.cut(cleanup(text)) for text in corpus]


def _init_worker():
    """Initializer for worker processes to ensure clean state."""
    global _seg
    _seg = None


def _tokenize_chunk(chunk: list[str]) -> list[list]:
    """worker: receives chunk (list[str])"""
    seg = _get_seg()
    return [seg.cut(cleanup(text)) for text in chunk]


def parallel_tokenize(corpus: list[str], chunk_size: int = 100) -> list[list[str]]:
    """
    Tokenize a list of texts in parallel using pkuseg for search mode.

    Args:
        corpus (list[str]): A list of texts to be tokenized.
        chunk_size (int): The number of texts to process in each chunk.

    Returns:
        list[list[str]]: A list where each element is a list of tokens.
    """
    if not corpus:
        return []

    if len(corpus) < chunk_size:
        return tokenize(corpus)

    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing

    global _executor
    if _executor is None:
        # Limit max workers to avoid OOM (pkuseg models are large)
        # Using 4 workers is usually sufficient for most user loads
        max_workers = min(multiprocessing.cpu_count(), 4)
        # Use spawn context to ensure thread safety on Linux
        # Forking from a multi-threaded process (NiceGUI/Asyncio) is unsafe
        ctx = multiprocessing.get_context("spawn")
        _executor = ProcessPoolExecutor(
            max_workers=max_workers, mp_context=ctx, initializer=_init_worker
        )

    def chunk_gen():
        for i in range(0, len(corpus), chunk_size):
            yield corpus[i : i + chunk_size]

    # Use the global executor to tokenize chunks in parallel
    results = _executor.map(_tokenize_chunk, chunk_gen())

    final_result = []
    for chunk_res in results:
        final_result.extend(chunk_res)

    return final_result
