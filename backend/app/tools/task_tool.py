from typing import Any

from app.tools.mcp_client import MCPClient


class TaskTool:
    def __init__(self, mcp_client: MCPClient) -> None:
        self.mcp_client = mcp_client

    async def create_task(self, title: str) -> dict[str, Any]:
        payload = {"title": title}
        tool_response = await self.mcp_client.call_tool("tasks.create_task", payload)
        if tool_response.get("status") != "success":
            return {"status": "fallback", **payload}
        return {"status": "success", **payload, "external": tool_response.get("result", {})}
