from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=128)
    email: str
    role: Literal["user", "admin"] = "user"


class UserRecord(BaseModel):
    user_id: str
    email: str
    role: str
    created_at: datetime


class TaskRecord(BaseModel):
    task_id: str
    user_id: str
    title: str = Field(min_length=1, max_length=300)
    status: Literal["todo", "in_progress", "done"] = "todo"
    deadline: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EventRecord(BaseModel):
    event_id: str
    user_id: str
    title: str = Field(min_length=1, max_length=300)
    start_time: datetime
    end_time: datetime
    location: str | None = None
    created_at: datetime


class NoteRecord(BaseModel):
    note_id: str
    user_id: str
    content: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class AgentLogRecord(BaseModel):
    log_id: str
    user_id: str
    agent_name: str
    action: str
    status: Literal["success", "failure"]
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class WorkflowRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()


class AgentMessage(BaseModel):
    agent: str
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    summary: str
    actions: list[dict[str, Any]]
    recommendations: list[str]


class CascadeTestRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=256)
    change_type: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


class CascadeTestResponse(BaseModel):
    cascade_id: str
    updated_nodes: list[dict[str, Any]]
    logs: list[dict[str, Any]]
    summary: str
