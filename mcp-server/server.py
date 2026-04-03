from __future__ import annotations

from importlib import import_module
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tools.calendar import create_calendar_event, update_calendar_event
from tools.notes import create_note
from tools.tasks import manage_tasks

app = FastAPI(title="Productivity MCP Server")
FastMCP = getattr(import_module("mcp.server.fastmcp"), "FastMCP")
mcp = FastMCP("productivity-mcp")


class RpcPayload(BaseModel):
    jsonrpc: str
    id: str | int
    method: str
    params: dict[str, Any]


TOOLS = {
    "create_calendar_event": create_calendar_event,
    "update_calendar_event": update_calendar_event,
    "manage_tasks": manage_tasks,
    "create_note": create_note,
}


@mcp.tool()
def create_calendar_event_tool(title: str, start_time: str, end_time: str, location: str | None = None) -> dict[str, Any]:
    return create_calendar_event(title=title, start_time=start_time, end_time=end_time, location=location)


@mcp.tool()
def update_calendar_event_tool(
    event_id: str,
    start_time: str,
    end_time: str,
    title: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    return update_calendar_event(
        event_id=event_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        location=location,
    )


@mcp.tool()
def manage_tasks_tool(
    action: str,
    title: str | None = None,
    status: str | None = None,
    deadline: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    return manage_tasks(action=action, title=title, status=status, deadline=deadline, task_id=task_id)


@mcp.tool()
def create_note_tool(content: str, tags: list[str] | None = None) -> dict[str, Any]:
    return create_note(content=content, tags=tags)


@app.post("/rpc")
async def rpc(payload: RpcPayload) -> dict[str, Any]:
    if payload.method != "tools/call":
        raise HTTPException(status_code=400, detail="Unsupported method")

    name = payload.params.get("name")
    arguments = payload.params.get("arguments", {})
    if name not in TOOLS:
        return {
            "jsonrpc": "2.0",
            "id": payload.id,
            "error": {"code": -32601, "message": f"Unknown tool {name}"},
        }

    result = TOOLS[name](**arguments)
    return {
        "jsonrpc": "2.0",
        "id": payload.id,
        "result": result,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    # Official MCP SDK runtime entrypoint (stdio transport).
    mcp.run()
