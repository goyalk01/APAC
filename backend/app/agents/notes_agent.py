from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.db.repositories import Repository
from app.mcp_client.client import MCPToolClient


class NotesAgent(BaseAgent):
    def __init__(self, repository: Repository, mcp_client: MCPToolClient) -> None:
        super().__init__(name="notes_agent")
        self.repository = repository
        self.mcp_client = mcp_client

    async def handle(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        content = payload.get("content", "")
        call_args = {
            "content": content,
            "tags": payload.get("tags", []),
        }
        tool_result = await self.mcp_client.call_tool("create_note", call_args)
        created = await self.repository.create_note(
            {
                "user_id": user_id,
                "content": content,
                "tags": payload.get("tags", []),
                "tool_status": tool_result.get("status"),
            }
        )
        return {"agent": self.name, "result": created, "tool": tool_result}
