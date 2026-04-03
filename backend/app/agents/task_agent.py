from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.db.repositories import Repository
from app.mcp_client.client import MCPToolClient


class TaskAgent(BaseAgent):
    def __init__(self, repository: Repository, mcp_client: MCPToolClient) -> None:
        super().__init__(name="task_agent")
        self.repository = repository
        self.mcp_client = mcp_client

    async def handle(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        call_args = {
            "action": payload.get("action", "create"),
            "title": payload.get("title", "Untitled task"),
            "status": payload.get("status", "todo"),
            "deadline": payload.get("deadline"),
            "task_id": payload.get("task_id"),
        }
        tool_result = await self.mcp_client.call_tool("manage_tasks", call_args)
        created = await self.repository.create_task(
            {
                "user_id": user_id,
                "title": call_args["title"],
                "status": call_args["status"],
                "deadline": payload.get("deadline"),
                "tool_status": tool_result.get("status"),
            }
        )
        return {"agent": self.name, "result": created, "tool": tool_result}
