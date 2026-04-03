from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any


class FirestoreStore:
    def __init__(self) -> None:
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self.database = os.getenv("FIRESTORE_DATABASE", "(default)")
        self._fallback: dict[str, dict[str, dict[str, Any]]] = {
            "tasks": {},
            "events": {},
            "notes": {},
        }

        self.client = None
        if self.project:
            try:
                from google.cloud import firestore

                self.client = firestore.Client(project=self.project, database=self.database)
            except Exception:
                self.client = None

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save(self, collection: str, payload: dict[str, Any], id_field: str) -> dict[str, Any]:
        resource_id = payload.get(id_field) or str(uuid.uuid4())
        data = {id_field: resource_id, "updated_at": self._now(), **payload}
        if self.client is None:
            self._fallback[collection][resource_id] = data
            return data

        self.client.collection(collection).document(resource_id).set(data)
        return data

    def list_tasks(self) -> list[dict[str, Any]]:
        if self.client is None:
            return list(self._fallback["tasks"].values())
        docs = self.client.collection("tasks").stream()
        return [doc.to_dict() for doc in docs]

    def list_collection(self, collection: str) -> list[dict[str, Any]]:
        if self.client is None:
            return list(self._fallback.get(collection, {}).values())
        docs = self.client.collection(collection).stream()
        return [doc.to_dict() for doc in docs]
