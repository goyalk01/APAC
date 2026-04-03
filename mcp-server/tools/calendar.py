from __future__ import annotations

from typing import Any

from tools.firestore_store import FirestoreStore

store = FirestoreStore()


def create_calendar_event(title: str, start_time: str, end_time: str, location: str | None = None) -> dict[str, Any]:
    event = store.save(
        "events",
        {
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "source": "mcp",
        },
        "event_id",
    )
    return {"status": "success", "event": event}


def update_calendar_event(
    event_id: str,
    start_time: str,
    end_time: str,
    title: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    event = store.save(
        "events",
        {
            "event_id": event_id,
            "title": title or "Updated event",
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "source": "mcp",
        },
        "event_id",
    )
    return {"status": "success", "event": event}
