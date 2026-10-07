"""Minimal Home Assistant WebSocket client (read-only automation traces).

Handles HA's binary frames (pings) and the auth handshake. Used by the
automation test kit to read traces and list automations.
"""
from __future__ import annotations

import json

import aiohttp


class HAClient:
    def __init__(self, url: str, token: str) -> None:
        ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
        self._ws_url = ws_url.rstrip("/") + "/api/websocket"
        self._token = token
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._id = 0

    async def connect(self) -> None:
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(
            self._ws_url, heartbeat=30, max_msg_size=64 * 1024 * 1024
        )
        msg = await self._receive()
        if msg.get("type") != "auth_required":
            raise RuntimeError(f"expected auth_required, got {msg}")
        await self._ws.send_json({"type": "auth", "access_token": self._token})
        msg = await self._receive()
        if msg.get("type") != "auth_ok":
            raise RuntimeError(f"auth failed: {msg}")

    async def _receive(self) -> dict:
        assert self._ws is not None
        while True:
            ws_msg = await self._ws.receive()
            if ws_msg.type == aiohttp.WSMsgType.TEXT:
                return json.loads(ws_msg.data)
            if ws_msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                raise RuntimeError(f"websocket closed: {ws_msg.type}")
            # skip BINARY / PING / PONG / CLOSING frames

    async def request(self, type_: str, **data) -> dict:
        """Send a command and return its response (matched by id)."""
        assert self._ws is not None
        self._id += 1
        msg_id = self._id
        await self._ws.send_json({"id": msg_id, "type": type_, **data})
        while True:
            msg = await self._receive()
            if msg.get("id") == msg_id:
                return msg

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._session is not None:
            await self._session.close()


async def list_traces(
    client: HAClient, domain: str = "automation", item_id: str | None = None
) -> list[dict]:
    """Return trace summaries for a domain (or a single item)."""
    data: dict = {"domain": domain}
    if item_id is not None:
        data["item_id"] = item_id
    resp = await client.request("trace/list", **data)
    if not resp.get("success"):
        raise RuntimeError(f"trace/list failed: {resp}")
    return resp.get("result", [])


async def get_trace(
    client: HAClient, domain: str, item_id: str, run_id: str
) -> dict:
    """Return the full trace dict for a given run."""
    resp = await client.request(
        "trace/get", domain=domain, item_id=item_id, run_id=run_id
    )
    if not resp.get("success"):
        raise RuntimeError(f"trace/get failed: {resp}")
    return resp.get("result", {})


async def list_automation_entities(client: HAClient) -> list[dict]:
    """Return automation entities from the entity registry."""
    resp = await client.request("config/entity_registry/list")
    if not resp.get("success"):
        raise RuntimeError(f"entity_registry/list failed: {resp}")
    return [
        e for e in resp.get("result", [])
        if e.get("entity_id", "").startswith("automation.")
    ]
