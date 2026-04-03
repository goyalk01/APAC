from __future__ import annotations

from typing import Any

from tools.firestore_store import FirestoreStore

store = FirestoreStore()


def manage_tasks(
    action: str,
    title: str | None = None,
    status: str | None = None,
    deadline: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    if action == "list":
        return {"status": "success", "items": store.list_tasks()}

    task = store.save(
        "tasks",
        {
            "task_id": task_id,
            "title": title or "Untitled task",
            "status": status or "todo",
            "deadline": deadline,
            "source": "mcp",
        },
        "task_id",
    )
    return {"status": "success", "task": task}
