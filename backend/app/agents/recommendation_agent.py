from __future__ import annotations

from app.agents.base import BaseAgent
from app.db.repositories import Repository


class RecommendationAgent(BaseAgent):
    def __init__(self, repository: Repository) -> None:
        super().__init__(name="recommendation_agent")
        self.repository = repository

    async def handle(self, user_id: str, payload: dict) -> dict:
        tasks = await self.repository.list_tasks(user_id)
        events = await self.repository.list_events(user_id)

        suggestions: list[str] = []
        if len(tasks) >= 5:
            suggestions.append("You have many open tasks. Consider prioritizing top 3 for tomorrow.")
        if len(events) >= 3:
            suggestions.append("Your calendar is busy. Add 15-minute buffers between meetings.")
        if not suggestions:
            suggestions.append("Your plan looks balanced. Keep notes updated for better recommendations.")

        return {"agent": self.name, "result": {"suggestions": suggestions}}
