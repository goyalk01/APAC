from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    description: str
    parameters: dict


FUNCTION_SPECS: list[FunctionSpec] = [
    FunctionSpec(
        name="create_calendar_event",
        description="Create a calendar event for the user and persist it.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_time": {"type": "string", "description": "ISO-8601 timestamp"},
                "end_time": {"type": "string", "description": "ISO-8601 timestamp"},
                "location": {"type": "string"},
            },
            "required": ["title", "start_time", "end_time"],
        },
    ),
    FunctionSpec(
        name="manage_tasks",
        description="Create or update a task in task management.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update", "list"]},
                "title": {"type": "string"},
                "status": {"type": "string", "enum": ["todo", "in_progress", "done"]},
                "deadline": {"type": "string", "description": "ISO-8601 timestamp"},
                "task_id": {"type": "string"},
            },
            "required": ["action"],
        },
    ),
    FunctionSpec(
        name="update_calendar_event",
        description="Update an existing calendar event.",
        parameters={
            "type": "object",
            "properties": {
                "event_id": {"type": "string"},
                "title": {"type": "string"},
                "start_time": {"type": "string", "description": "ISO-8601 timestamp"},
                "end_time": {"type": "string", "description": "ISO-8601 timestamp"},
                "location": {"type": "string"},
            },
            "required": ["event_id", "start_time", "end_time"],
        },
    ),
    FunctionSpec(
        name="create_note",
        description="Create a note associated with the user context.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["content"],
        },
    ),
    FunctionSpec(
        name="trigger_cascade",
        description="Propagate changes across dependent tasks/events",
        parameters={
            "type": "object",
            "properties": {
                "node_id": {"type": "string"},
                "change_type": {"type": "string"},
                "payload": {"type": "object"},
            },
            "required": ["node_id", "change_type"],
        },
    ),
    FunctionSpec(
        name="create_dependency",
        description="Create dependency between tasks/events",
        parameters={
            "type": "object",
            "properties": {
                "parent_id": {"type": "string"},
                "child_id": {"type": "string"},
                "dependency_type": {"type": "string"},
            },
            "required": ["parent_id", "child_id"],
        },
    ),
]
