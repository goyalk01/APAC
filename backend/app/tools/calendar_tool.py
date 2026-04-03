from datetime import datetime, timedelta, timezone
from typing import Any

from app.tools.mcp_client import MCPClient


class CalendarTool:
    def __init__(self, mcp_client: MCPClient) -> None:
        self.mcp_client = mcp_client

    async def create_event(self, title: str, start_time: datetime | None = None) -> dict[str, Any]:
        event_start = start_time or (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        payload = {
            "title": title,
            "start_time": event_start.isoformat(),
            "end_time": (event_start + timedelta(hours=1)).isoformat(),
        }
        tool_response = await self.mcp_client.call_tool("calendar.create_event", payload)
        if tool_response.get("status") != "success":
            # Fallback keeps workflow resilient when the external tool is down.
            return {"status": "fallback", **payload}
        return {"status": "success", **payload, "external": tool_response.get("result", {})}
