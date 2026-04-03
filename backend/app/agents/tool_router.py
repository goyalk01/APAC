from __future__ import annotations

from app.agents.calendar_agent import CalendarAgent
from app.agents.notes_agent import NotesAgent
from app.agents.task_agent import TaskAgent


class ToolRouter:
    def __init__(self, task_agent: TaskAgent, calendar_agent: CalendarAgent, notes_agent: NotesAgent) -> None:
        self.task_agent = task_agent
        self.calendar_agent = calendar_agent
        self.notes_agent = notes_agent

    async def execute(self, user_id: str, tool_name: str, args: dict) -> dict:
        if tool_name == "manage_tasks":
            payload = await self.task_agent.handle(user_id, args)
            return {"status": "success", "result": payload}
        if tool_name in {"create_calendar_event", "update_calendar_event"}:
            payload = await self.calendar_agent.handle(user_id, args)
            return {"status": "success", "result": payload}
        if tool_name == "create_note":
            payload = await self.notes_agent.handle(user_id, args)
            return {"status": "success", "result": payload}
        return {"status": "failure", "error": f"Unknown tool {tool_name}"}
