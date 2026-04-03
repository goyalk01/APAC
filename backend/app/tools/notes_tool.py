from typing import Any

from app.tools.mcp_client import MCPClient


class NotesTool:
    def __init__(self, mcp_client: MCPClient) -> None:
        self.mcp_client = mcp_client

    async def create_note(self, content: str) -> dict[str, Any]:
        payload = {"content": content}
        tool_response = await self.mcp_client.call_tool("notes.create_note", payload)
        if tool_response.get("status") != "success":
            return {"status": "fallback", **payload}
        return {"status": "success", **payload, "external": tool_response.get("result", {})}
