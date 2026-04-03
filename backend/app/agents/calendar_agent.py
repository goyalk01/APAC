from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.agents.base import BaseAgent
from app.db.repositories import Repository
from app.mcp_client.client import MCPToolClient


class CalendarAgent(BaseAgent):
    def __init__(self, repository: Repository, mcp_client: MCPToolClient) -> None:
        super().__init__(name="calendar_agent")
        self.repository = repository
        self.mcp_client = mcp_client

    async def handle(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        title = payload.get("title", "New meeting")
        event_id = payload.get("event_id")
        start_time = payload.get("start_time") or (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        ).isoformat()
        end_time = payload.get("end_time") or (datetime.fromisoformat(start_time) + timedelta(hours=1)).isoformat()
        call_args = {
            "event_id": event_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "location": payload.get("location"),
        }
        tool_name = "update_calendar_event" if event_id else "create_calendar_event"
        tool_result = await self.mcp_client.call_tool(tool_name, call_args)
        created = await self.repository.create_event(
            {
                "event_id": event_id,
                "user_id": user_id,
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "location": payload.get("location"),
                "tool_status": tool_result.get("status"),
            }
        )
        return {"agent": self.name, "result": created, "tool": tool_result}
