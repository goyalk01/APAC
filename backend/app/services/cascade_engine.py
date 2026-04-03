from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.repositories import Repository
from app.mcp_client.client import MCPToolClient
from app.services.dependency_engine import DependencyEngine


class CascadeEngine:
    def __init__(self, repository: Repository, dependency_engine: DependencyEngine, mcp_client: MCPToolClient) -> None:
        self.repository = repository
        self.dependency_engine = dependency_engine
        self.mcp_client = mcp_client

    async def cascade_update(
        self,
        user_id: str,
        node_id: str,
        change_type: str,
        payload: dict,
        cascade_id: str | None = None,
        visited: set[str] | None = None,
    ) -> dict:
        cascade_id = cascade_id or str(uuid4())
        visited = visited or set()
        if node_id in visited:
            return {"cascade_id": cascade_id, "updated_nodes": [], "logs": []}

        visited.add(node_id)
        dependents = await self.dependency_engine.get_dependents(node_id)
        updated_nodes: list[dict] = []
        logs: list[dict] = []

        for dep in dependents:
            child_id = dep["child_id"]
            reason = self._reason_text(parent_id=node_id, child_id=child_id, change_type=change_type, payload=payload)
            action = self._infer_action(child_id=child_id, change_type=change_type, payload=payload)
            tool_result = await self._execute_action(action)

            if action["tool"] == "manage_tasks":
                await self.repository.create_task(
                    {
                        "task_id": action["arguments"].get("task_id") or child_id,
                        "user_id": user_id,
                        "title": action["arguments"].get("title", "Cascade-updated task"),
                        "status": action["arguments"].get("status", "todo"),
                        "deadline": action["arguments"].get("deadline"),
                        "tool_status": tool_result.get("status"),
                    }
                )
            elif action["tool"] == "update_calendar_event":
                await self.repository.create_event(
                    {
                        "event_id": action["arguments"].get("event_id") or child_id,
                        "user_id": user_id,
                        "title": action["arguments"].get("title", "Cascade-updated event"),
                        "start_time": action["arguments"].get("start_time"),
                        "end_time": action["arguments"].get("end_time"),
                        "location": action["arguments"].get("location"),
                        "tool_status": tool_result.get("status"),
                    }
                )

            note_result = await self.mcp_client.call_tool(
                "create_note",
                {
                    "content": reason,
                    "tags": ["cascade", change_type],
                },
            )
            await self.repository.create_note(
                {
                    "user_id": user_id,
                    "content": reason,
                    "tags": ["cascade", change_type],
                    "tool_status": note_result.get("status"),
                }
            )

            log = await self.repository.create_agent_log(
                {
                    "user_id": user_id,
                    "agent_name": "cascade_engine",
                    "action": action["tool"],
                    "status": "success" if tool_result.get("status") == "success" else "failure",
                    "reason": reason,
                    "affected_nodes": [node_id, child_id],
                    "details": {
                        "cascade_id": cascade_id,
                        "change_type": change_type,
                        "arguments": action["arguments"],
                        "tool_result": tool_result,
                    },
                }
            )

            updated_nodes.append({"node_id": child_id, "tool": action["tool"], "result": tool_result})
            logs.append(log)

            nested = await self.cascade_update(
                user_id=user_id,
                node_id=child_id,
                change_type=change_type,
                payload=payload,
                cascade_id=cascade_id,
                visited=visited,
            )
            updated_nodes.extend(nested["updated_nodes"])
            logs.extend(nested["logs"])

        summary = f"Cascade {cascade_id} updated {len(updated_nodes)} dependent nodes from {node_id}."
        return {
            "cascade_id": cascade_id,
            "updated_nodes": updated_nodes,
            "logs": logs,
            "summary": summary,
        }

    async def undo_cascade(self, user_id: str, cascade_id: str) -> dict:
        logs = await self.repository.list_agent_logs(user_id)
        matched = [log for log in logs if log.get("details", {}).get("cascade_id") == cascade_id]
        return {
            "cascade_id": cascade_id,
            "reverted": False,
            "summary": f"Undo placeholder: found {len(matched)} cascade log entries for {cascade_id}.",
        }

    async def _execute_action(self, action: dict) -> dict:
        return await self.mcp_client.call_tool(action["tool"], action["arguments"])

    def _infer_action(self, child_id: str, change_type: str, payload: dict) -> dict:
        if child_id.startswith("event_"):
            start_time = payload.get("new_start_time") or datetime.now(timezone.utc).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
            end_time = payload.get("new_end_time") or (datetime.fromisoformat(start_time) + timedelta(hours=1)).isoformat()
            return {
                "tool": "update_calendar_event",
                "arguments": {
                    "event_id": child_id,
                    "title": payload.get("title", "Cascade-adjusted event"),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": payload.get("location"),
                },
            }

        deadline = payload.get("new_deadline")
        if not deadline and payload.get("new_start_time"):
            deadline = (datetime.fromisoformat(payload["new_start_time"]) + timedelta(hours=1)).isoformat()
        if not deadline:
            deadline = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()

        return {
            "tool": "manage_tasks",
            "arguments": {
                "action": "update",
                "task_id": child_id,
                "title": payload.get("title", "Cascade-adjusted task"),
                "status": "todo",
                "deadline": deadline,
            },
        }

    def _reason_text(self, parent_id: str, child_id: str, change_type: str, payload: dict) -> str:
        old_time = payload.get("old_start_time", "unknown")
        new_time = payload.get("new_start_time", "unknown")
        return (
            f"{child_id} was rescheduled because {parent_id} changed ({change_type}) "
            f"from {old_time} to {new_time}."
        )
