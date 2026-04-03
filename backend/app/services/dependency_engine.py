from __future__ import annotations

from app.db.repositories import Repository


class DependencyEngine:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    async def add_dependency(self, parent_id: str, child_id: str, type: str) -> dict:
        return await self.repository.add_dependency(parent_id=parent_id, child_id=child_id, relation_type=type)

    async def get_dependents(self, node_id: str) -> list[dict]:
        return await self.repository.get_dependents(node_id)

    async def get_dependencies(self, node_id: str) -> list[dict]:
        return await self.repository.get_dependencies(node_id)
