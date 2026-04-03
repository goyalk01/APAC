from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, base_url: str, timeout_seconds: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def call_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url:
            return {"status": "unavailable", "reason": "mcp_url_not_configured"}

        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": payload,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/rpc", json=body)
                response.raise_for_status()
                data = response.json()
                return {"status": "success", "result": data.get("result", {})}
        except Exception as exc:
            logger.exception("MCP tool call failed", extra={"tool_name": tool_name})
            return {"status": "failure", "reason": str(exc)}
