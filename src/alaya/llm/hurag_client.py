import asyncio
from httpx import AsyncClient

_clients: dict[str, AsyncClient] = {}
_clients_lock: asyncio.Lock = asyncio.Lock()

def create_client(
    base_url: str,
    timeout: float = 60.0,
) -> AsyncClient:
    ...

async def get_hurag_client(
    base_url: str | None = None,
    timeout: float = 60.0,
    *,
    client_name: str = "default",
) -> AsyncClient:
    """Get or create an httpx.AsyncClient to HuRAG API server"""
    from .. import conf
    base_url = base_url or conf.service.hurag_server

    global _clients

    if client_name in _clients:
        return _clients[client_name]

    async with _clients_lock:
        if client_name in _clients:
            return _clients[client_name]
    ...
