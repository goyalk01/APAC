from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import AsyncGenerator, Awaitable, Callable

from app.db.repositories import Repository
from app.mcp_client.client import MCPToolClient
from app.services.dependency_engine import DependencyEngine
from app.services.llm_service import LLMService


class CascadeEngine:
    MAX_DEPTH = 5

    def __init__(
        self,
        repository: Repository,
        dependency_engine: DependencyEngine,
        mcp_client: MCPToolClient,
        llm_service: LLMService,
    ) -> None:
        self.repository = repository
        self.dependency_engine = dependency_engine
        self.mcp_client = mcp_client
        self.llm_service = llm_service

    async def cascade_update(
        self,
        user_id: str,
        node_id: str,
        change_type: str,
        payload: dict,
        cascade_id: str | None = None,
        visited: set[str] | None = None,
        depth: int = 0,
        progress_callback: Callable[[dict], Awaitable[None]] | None = None,
    ) -> dict:
        cascade_id = cascade_id or str(uuid4())
        visited = visited or set()
        if depth > self.MAX_DEPTH:
            return {
                "cascade_id": cascade_id,
                "updated_nodes": [],
                "logs": [],
                "summary": f"Max cascade depth reached at node {node_id}.",
            }
        if node_id in visited:
            return {"cascade_id": cascade_id, "updated_nodes": [], "logs": [], "summary": "Visited node skipped."}

        visited.add(node_id)
        dependents = await self.dependency_engine.get_dependents(node_id)
        updated_nodes: list[dict] = []
        timeline: list[dict] = []
        logs: list[dict] = []

        if progress_callback:
            await progress_callback({"node_id": node_id, "status": "processing", "cascade_id": cascade_id})

        for dep in dependents:
            child_id = dep["child_id"]
            if child_id in visited:
                continue

            reason = self._reason_text(parent_id=node_id, child_id=child_id, change_type=change_type, payload=payload)
            action = await self._infer_action(
                user_id=user_id,
                parent_id=node_id,
                child_id=child_id,
                change_type=change_type,
                payload=payload,
            )

            previous_state = None
            if action["tool"] == "manage_tasks":
                previous_state = await self.repository.get_task(action["arguments"].get("task_id") or child_id)
            elif action["tool"] == "update_calendar_event":
                previous_state = await self.repository.get_event(action["arguments"].get("event_id") or child_id)

            if progress_callback:
                await progress_callback({"node_id": child_id, "status": "updating", "cascade_id": cascade_id})

            try:
                tool_result = await self._execute_action(action)
            except Exception as exc:
                failure_log = await self.repository.create_agent_log(
                    {
                        "user_id": user_id,
                        "agent_name": "cascade_engine",
                        "action": action["tool"],
                        "status": "failure",
                        "reason": str(exc),
                        "affected_nodes": [node_id, child_id],
                        "details": {
                            "cascade_id": cascade_id,
                            "change_type": change_type,
                            "node_id": child_id,
                            "arguments": action["arguments"],
                        },
                    }
                )
                logs.append(failure_log)
                if progress_callback:
                    await progress_callback({"node_id": child_id, "status": "failed", "cascade_id": cascade_id, "reason": str(exc)})
                continue

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
                        "node_id": child_id,
                        "arguments": action["arguments"],
                        "previous_state": previous_state,
                        "tool_result": tool_result,
                    },
                }
            )

            updated_nodes.append({"node_id": child_id, "tool": action["tool"], "result": tool_result})
            timeline.append({"node": child_id, "action": action["tool"]})
            logs.append(log)

            if progress_callback:
                await progress_callback({"node_id": child_id, "status": "updated", "cascade_id": cascade_id, "reason": reason})

            nested = await self.cascade_update(
                user_id=user_id,
                node_id=child_id,
                change_type=change_type,
                payload=payload,
                cascade_id=cascade_id,
                visited=visited,
                depth=depth + 1,
                progress_callback=progress_callback,
            )
            updated_nodes.extend(nested["updated_nodes"])
            timeline.extend(nested.get("timeline", []))
            logs.extend(nested["logs"])

        summary = f"Cascade {cascade_id} updated {len(updated_nodes)} dependent nodes from {node_id}."
        ordered_timeline = [{"step": index + 1, **item} for index, item in enumerate(timeline)]
        return {
            "cascade_id": cascade_id,
            "updated_nodes": updated_nodes,
            "timeline": ordered_timeline,
            "logs": logs,
            "summary": summary,
        }

    async def cascade_update_stream(
        self,
        user_id: str,
        node_id: str,
        change_type: str,
        payload: dict,
    ) -> AsyncGenerator[dict, None]:
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def emit(event: dict) -> None:
            await queue.put(event)

        async def runner() -> None:
            result = await self.cascade_update(
                user_id=user_id,
                node_id=node_id,
                change_type=change_type,
                payload=payload,
                progress_callback=emit,
            )
            await queue.put({"status": "complete", "summary": result.get("summary"), "cascade_id": result.get("cascade_id")})
            await queue.put(None)

        task = asyncio.create_task(runner())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            if not task.done():
                task.cancel()

    async def undo_cascade(self, user_id: str, cascade_id: str) -> dict:
        logs = await self.repository.list_agent_logs(user_id)
        matched = [log for log in logs if log.get("details", {}).get("cascade_id") == cascade_id and log.get("agent_name") == "cascade_engine"]

        reverted_count = 0
        for log in sorted(matched, key=lambda l: l.get("timestamp", ""), reverse=True):
            action = log.get("action")
            details = log.get("details", {})
            previous = details.get("previous_state") or {}
            node_id = details.get("node_id")

            if action == "update_calendar_event" and previous:
                revert_args = {
                    "event_id": previous.get("event_id") or node_id,
                    "title": previous.get("title"),
                    "start_time": previous.get("start_time"),
                    "end_time": previous.get("end_time"),
                    "location": previous.get("location"),
                }
                result = await self.mcp_client.call_tool("update_calendar_event", revert_args)
                if result.get("status") == "success":
                    reverted_count += 1

            if action == "manage_tasks" and previous:
                revert_args = {
                    "action": "update",
                    "task_id": previous.get("task_id") or node_id,
                    "title": previous.get("title"),
                    "status": previous.get("status"),
                    "deadline": previous.get("deadline"),
                }
                result = await self.mcp_client.call_tool("manage_tasks", revert_args)
                if result.get("status") == "success":
                    reverted_count += 1

        await self.repository.create_agent_log(
            {
                "user_id": user_id,
                "agent_name": "cascade_engine",
                "action": "undo_cascade",
                "status": "success",
                "reason": "Undo executed for cascade id",
                "affected_nodes": [log.get("details", {}).get("node_id") for log in matched if log.get("details", {}).get("node_id")],
                "details": {"cascade_id": cascade_id, "reverted_count": reverted_count},
            }
        )

        return {
            "cascade_id": cascade_id,
            "reverted": reverted_count > 0,
            "summary": f"Undo completed: reverted {reverted_count} actions for cascade {cascade_id}.",
        }

    async def _execute_action(self, action: dict) -> dict:
        return await self.mcp_client.call_tool(action["tool"], action["arguments"])

    async def _infer_action(self, user_id: str, parent_id: str, child_id: str, change_type: str, payload: dict) -> dict:
        user_schedule = await self.repository.list_events(user_id)
        context = {
            "changed_node": parent_id,
            "change_type": change_type,
            "change_payload": payload,
            "user_schedule": user_schedule,
            "dependent_task": child_id,
        }
        decision = await self.llm_service.generate_structured_output(
            prompt="Find next non-conflicting time slot",
            context=context,
        )

        llm_start = decision.get("start_time")
        llm_end = decision.get("end_time")
        if not llm_start:
            llm_start = payload.get("new_start_time") or datetime.now(timezone.utc).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
        if not llm_end:
            llm_end = payload.get("new_end_time") or (datetime.fromisoformat(llm_start) + timedelta(hours=1)).isoformat()

        if child_id.startswith("event_"):
            return {
                "tool": "update_calendar_event",
                "arguments": {
                    "event_id": child_id,
                    "title": payload.get("title", "Cascade-adjusted event"),
                    "start_time": llm_start,
                    "end_time": llm_end,
                    "location": payload.get("location"),
                },
            }

        deadline = payload.get("new_deadline") or llm_end
        if not deadline:
            deadline = (datetime.fromisoformat(llm_start) + timedelta(hours=1)).isoformat()

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
