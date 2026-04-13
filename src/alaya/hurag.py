import json
import asyncio
from httpx import AsyncClient, Timeout, Limits
from typing import Any
from collections.abc import AsyncGenerator


_clients: dict[str, AsyncClient] = {}
_clients_lock: asyncio.Lock = asyncio.Lock()


def create_client(
    base_url: str,
    timeout: float = 60.0,
) -> AsyncClient:
    _client = AsyncClient(
        base_url=base_url,
        timeout=Timeout(connect=20.0, read=timeout, write=timeout, pool=60.0),
        limits=Limits(keepalive_expiry=60.0)
    )
    return _client


async def get_client(
    base_url: str | None = None,
    timeout: float = 60.0,
    *,
    client_name: str = "default",
) -> AsyncClient:
    """Get or create an httpx.AsyncClient to HuRAG API server"""
    from . import conf
    base_url = base_url or str(conf.service.hurag_server)
    client_name = client_name or "default"

    global _clients

    if client_name in _clients:
        return _clients[client_name]

    async with _clients_lock:
        if client_name in _clients:
            return _clients[client_name]

        _clients[client_name] = create_client(base_url=base_url, timeout=timeout)

    return _clients[client_name]


async def close_client(client_name: str | None = None) -> None:
    global _clients

    if client_name:
        if client_name in _clients:
            cli = _clients.pop(client_name)
            await cli.aclose()
    else:
        for cli in _clients.values():
            await cli.aclose()
        _clients.clear()


async def get(url: str, *, data: Any = None, client_name: str = "default") -> Any:
    cli = await get_client(client_name=client_name)
    response = await cli.get(url, params=data)
    response.raise_for_status()
    return json.loads(response.text)


async def post(url: str, *, data: Any = None, client_name: str = "default") -> Any:
    cli = await get_client(client_name=client_name)
    response = await cli.post(url, json=data)
    response.raise_for_status()
    return json.loads(response.text)

async def chat(
    prompt: str,
    *,
    system_prompt: str | None = None,
    history: list[dict[str, str]] | None = None,
    temperature: float = 0.0,
    timeout: float = 180.0,
    client_name: str = "default",
) -> AsyncGenerator[str]:
    cli = await get_client(client_name=client_name)
    data = {"prompt": prompt, "temperature": temperature, "timeout": int(timeout)}
    if system_prompt:
        data["system_prompt"] = system_prompt
    if history:
        data["history"] = history
    async with cli.stream("POST", "v1/llm/chat", json=data) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line.removeprefix("data: ")
            if payload == "[DONE]":
                break
            yield json.loads(payload)["delta"]
