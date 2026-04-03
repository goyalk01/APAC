from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MCPToolClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": "tool-call",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/rpc", json=payload)
            response.raise_for_status()
            body = response.json()
            if "error" in body:
                return {"status": "failure", "error": body["error"]}
            return {"status": "success", "result": body.get("result", {})}
