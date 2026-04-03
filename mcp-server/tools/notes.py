from __future__ import annotations

from typing import Any

from tools.firestore_store import FirestoreStore

store = FirestoreStore()


def create_note(content: str, tags: list[str] | None = None) -> dict[str, Any]:
    note = store.save(
        "notes",
        {
            "content": content,
            "tags": tags or [],
            "source": "mcp",
        },
        "note_id",
    )
    return {"status": "success", "note": note}
