from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass
class InMemoryStore:
    users: dict[str, dict[str, Any]]
    tasks: dict[str, dict[str, Any]]
    events: dict[str, dict[str, Any]]
    notes: dict[str, dict[str, Any]]
    agent_logs: dict[str, dict[str, Any]]
    conversations: dict[str, dict[str, Any]]
    session_context: dict[str, dict[str, Any]]
    dependencies: dict[str, dict[str, Any]]


class Repository(Protocol):
    async def upsert_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def create_task(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def create_event(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def create_note(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def create_agent_log(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def list_tasks(self, user_id: str) -> list[dict[str, Any]]: ...
    async def list_events(self, user_id: str) -> list[dict[str, Any]]: ...
    async def list_notes(self, user_id: str) -> list[dict[str, Any]]: ...
    async def list_agent_logs(self, user_id: str | None = None) -> list[dict[str, Any]]: ...
    async def append_conversation_message(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def get_conversation(self, user_id: str) -> list[dict[str, Any]]: ...
    async def upsert_session_context(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    async def get_session_context(self, user_id: str) -> dict[str, Any]: ...
    async def add_dependency(self, parent_id: str, child_id: str, relation_type: str) -> dict[str, Any]: ...
    async def get_dependents(self, node_id: str) -> list[dict[str, Any]]: ...
    async def get_dependencies(self, node_id: str) -> list[dict[str, Any]]: ...
    async def list_dependencies(self) -> list[dict[str, Any]]: ...
    async def get_task(self, task_id: str) -> dict[str, Any] | None: ...
    async def get_event(self, event_id: str) -> dict[str, Any] | None: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self.store = InMemoryStore(
            users={},
            tasks={},
            events={},
            notes={},
            agent_logs={},
            conversations={},
            session_context={},
            dependencies={},
        )

    async def upsert_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        record = {"user_id": user_id, "created_at": payload.get("created_at", now), **payload}
        self.store.users[user_id] = record
        return record

    async def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = payload.get("task_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {"task_id": task_id, "created_at": now, "updated_at": now, **payload}
        self.store.tasks[task_id] = record
        return record

    async def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = payload.get("event_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {"event_id": event_id, "created_at": now, **payload}
        self.store.events[event_id] = record
        return record

    async def create_note(self, payload: dict[str, Any]) -> dict[str, Any]:
        note_id = payload.get("note_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {"note_id": note_id, "created_at": now, **payload}
        self.store.notes[note_id] = record
        return record

    async def create_agent_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        log_id = payload.get("log_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {"log_id": log_id, "timestamp": now, **payload}
        self.store.agent_logs[log_id] = record
        return record

    async def list_tasks(self, user_id: str) -> list[dict[str, Any]]:
        return [record for record in self.store.tasks.values() if record.get("user_id") == user_id]

    async def list_events(self, user_id: str) -> list[dict[str, Any]]:
        return [record for record in self.store.events.values() if record.get("user_id") == user_id]

    async def list_notes(self, user_id: str) -> list[dict[str, Any]]:
        return [record for record in self.store.notes.values() if record.get("user_id") == user_id]

    async def list_agent_logs(self, user_id: str | None = None) -> list[dict[str, Any]]:
        logs = list(self.store.agent_logs.values())
        if user_id is None:
            return logs
        return [record for record in logs if record.get("user_id") == user_id]

    async def append_conversation_message(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        message = {"timestamp": now, **payload}
        if user_id not in self.store.conversations:
            self.store.conversations[user_id] = {"user_id": user_id, "messages": []}
        self.store.conversations[user_id]["messages"].append(message)
        return message

    async def get_conversation(self, user_id: str) -> list[dict[str, Any]]:
        data = self.store.conversations.get(user_id, {"messages": []})
        return data.get("messages", [])

    async def upsert_session_context(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        record = {"user_id": user_id, "updated_at": now, **payload}
        self.store.session_context[user_id] = record
        return record

    async def get_session_context(self, user_id: str) -> dict[str, Any]:
        return self.store.session_context.get(user_id, {})

    async def add_dependency(self, parent_id: str, child_id: str, relation_type: str) -> dict[str, Any]:
        dependency_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "dependency_id": dependency_id,
            "parent_id": parent_id,
            "child_id": child_id,
            "type": relation_type,
            "created_at": now,
        }
        self.store.dependencies[dependency_id] = record
        return record

    async def get_dependents(self, node_id: str) -> list[dict[str, Any]]:
        return [dep for dep in self.store.dependencies.values() if dep.get("parent_id") == node_id]

    async def get_dependencies(self, node_id: str) -> list[dict[str, Any]]:
        return [dep for dep in self.store.dependencies.values() if dep.get("child_id") == node_id]

    async def list_dependencies(self) -> list[dict[str, Any]]:
        return list(self.store.dependencies.values())

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self.store.tasks.get(task_id)

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        return self.store.events.get(event_id)
