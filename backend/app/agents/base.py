from __future__ import annotations

from typing import Any


class BaseAgent:
    def __init__(self, name: str) -> None:
        self.name = name

    async def handle(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
