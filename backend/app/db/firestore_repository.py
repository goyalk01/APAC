from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.repositories import InMemoryRepository, Repository


class FirestoreRepository(Repository):
    def __init__(self, project: str, database: str) -> None:
        try:
            from google.cloud import firestore_async
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Firestore dependencies missing") from exc

        self.client = firestore_async.AsyncClient(project=project, database=database)

    async def upsert_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        data = {"user_id": user_id, "created_at": payload.get("created_at", now), **payload}
        await self.client.collection("users").document(user_id).set(data)
        return data

    async def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task_id = payload.get("task_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {"task_id": task_id, "created_at": now, "updated_at": now, **payload}
        await self.client.collection("tasks").document(task_id).set(data)
        return data

    async def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = payload.get("event_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {"event_id": event_id, "created_at": now, **payload}
        await self.client.collection("events").document(event_id).set(data)
        return data

    async def create_note(self, payload: dict[str, Any]) -> dict[str, Any]:
        note_id = payload.get("note_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {"note_id": note_id, "created_at": now, **payload}
        await self.client.collection("notes").document(note_id).set(data)
        return data

    async def create_agent_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        log_id = payload.get("log_id") or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {"log_id": log_id, "timestamp": now, **payload}
        await self.client.collection("agent_logs").document(log_id).set(data)
        return data

    async def list_tasks(self, user_id: str) -> list[dict[str, Any]]:
        query = self.client.collection("tasks").where("user_id", "==", user_id)
        docs = [doc async for doc in query.stream()]
        return [doc.to_dict() for doc in docs]

    async def list_events(self, user_id: str) -> list[dict[str, Any]]:
        query = self.client.collection("events").where("user_id", "==", user_id)
        docs = [doc async for doc in query.stream()]
        return [doc.to_dict() for doc in docs]

    async def list_notes(self, user_id: str) -> list[dict[str, Any]]:
        query = self.client.collection("notes").where("user_id", "==", user_id)
        docs = [doc async for doc in query.stream()]
        return [doc.to_dict() for doc in docs]

    async def list_agent_logs(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id is None:
            query = self.client.collection("agent_logs")
        else:
            query = self.client.collection("agent_logs").where("user_id", "==", user_id)
        docs = [doc async for doc in query.stream()]
        return [doc.to_dict() for doc in docs]

    async def append_conversation_message(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        message = {"timestamp": now, **payload}
        doc_ref = self.client.collection("conversations").document(user_id)
        snapshot = await doc_ref.get()
        current = snapshot.to_dict() if snapshot.exists else {"user_id": user_id, "messages": []}
        messages = current.get("messages", [])
        messages.append(message)
        await doc_ref.set({"user_id": user_id, "messages": messages}, merge=True)
        return message

    async def get_conversation(self, user_id: str) -> list[dict[str, Any]]:
        snapshot = await self.client.collection("conversations").document(user_id).get()
        if not snapshot.exists:
            return []
        return snapshot.to_dict().get("messages", [])

    async def upsert_session_context(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        data = {"user_id": user_id, "updated_at": now, **payload}
        await self.client.collection("session_context").document(user_id).set(data, merge=True)
        return data

    async def get_session_context(self, user_id: str) -> dict[str, Any]:
        snapshot = await self.client.collection("session_context").document(user_id).get()
        if not snapshot.exists:
            return {}
        return snapshot.to_dict()

    async def add_dependency(self, parent_id: str, child_id: str, relation_type: str) -> dict[str, Any]:
        dependency_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "dependency_id": dependency_id,
            "parent_id": parent_id,
            "child_id": child_id,
            "type": relation_type,
            "created_at": now,
        }
        await self.client.collection("dependencies").document(dependency_id).set(data)
        return data

    async def get_dependents(self, node_id: str) -> list[dict[str, Any]]:
        query = self.client.collection("dependencies").where("parent_id", "==", node_id)
        docs = [doc async for doc in query.stream()]
        return [doc.to_dict() for doc in docs]

    async def get_dependencies(self, node_id: str) -> list[dict[str, Any]]:
        query = self.client.collection("dependencies").where("child_id", "==", node_id)
        docs = [doc async for doc in query.stream()]
        return [doc.to_dict() for doc in docs]

    async def list_dependencies(self) -> list[dict[str, Any]]:
        docs = [doc async for doc in self.client.collection("dependencies").stream()]
        return [doc.to_dict() for doc in docs]

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        snapshot = await self.client.collection("tasks").document(task_id).get()
        if not snapshot.exists:
            return None
        return snapshot.to_dict()

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        snapshot = await self.client.collection("events").document(event_id).get()
        if not snapshot.exists:
            return None
        return snapshot.to_dict()


def build_repository(enable_firestore: bool, project: str, database: str) -> Repository:
    if enable_firestore and project:
        try:
            return FirestoreRepository(project=project, database=database)
        except Exception:
            return InMemoryRepository()
    return InMemoryRepository()
