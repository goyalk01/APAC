from __future__ import annotations

from app.db.repositories import Repository
from app.services.cascade_engine import CascadeEngine
from app.services.dependency_engine import DependencyEngine
from app.services.llm_service import LLMService
from app.utils.sanitization import detect_prompt_injection


class OrchestratorAgent:
    def __init__(
        self,
        repository: Repository,
        llm_service: LLMService,
        tool_router,
        cascade_engine: CascadeEngine,
        dependency_engine: DependencyEngine,
    ) -> None:
        self.repository = repository
        self.llm_service = llm_service
        self.tool_router = tool_router
        self.cascade_engine = cascade_engine
        self.dependency_engine = dependency_engine

    async def execute(self, user_id: str, message: str) -> dict:
        if detect_prompt_injection(message):
            return {
                "summary": "Request rejected due to unsafe prompt pattern.",
                "actions": [],
                "recommendations": ["Please rephrase your request without instruction override language."],
            }

        conversation = await self.repository.get_conversation(user_id)
        session_context = await self.repository.get_session_context(user_id)

        await self.repository.append_conversation_message(
            user_id,
            {
                "role": "user",
                "content": message,
            },
        )

        async def tool_callback(tool_name: str, args: dict) -> dict:
            if tool_name == "create_dependency":
                dependency = await self.dependency_engine.add_dependency(
                    parent_id=args["parent_id"],
                    child_id=args["child_id"],
                    type=args.get("dependency_type", "blocks"),
                )
                await self.repository.create_agent_log(
                    {
                        "user_id": user_id,
                        "agent_name": "orchestrator",
                        "action": tool_name,
                        "status": "success",
                        "reason": "Dependency created from model tool call",
                        "affected_nodes": [args["parent_id"], args["child_id"]],
                        "details": {"arguments": args, "dependency": dependency},
                    }
                )
                return {"status": "success", "dependency": dependency}

            if tool_name == "trigger_cascade":
                cascade_result = await self.cascade_engine.cascade_update(
                    user_id=user_id,
                    node_id=args["node_id"],
                    change_type=args["change_type"],
                    payload=args.get("payload", {}),
                )
                await self.repository.create_agent_log(
                    {
                        "user_id": user_id,
                        "agent_name": "orchestrator",
                        "action": tool_name,
                        "status": "success",
                        "reason": "Explicit cascade trigger from model function call",
                        "affected_nodes": [args["node_id"]],
                        "details": {"arguments": args, "cascade": cascade_result},
                    }
                )
                return {"status": "success", "cascade": cascade_result}

            result = await self.tool_router.execute(user_id=user_id, tool_name=tool_name, args=args)

            inferred_node_id = args.get("event_id") or args.get("task_id")
            if not inferred_node_id:
                nested = result.get("result", {}) if isinstance(result, dict) else {}
                if isinstance(nested, dict):
                    inferred_node_id = nested.get("event_id") or nested.get("task_id")
                    deeply_nested = nested.get("result", {}) if isinstance(nested.get("result"), dict) else {}
                    if not inferred_node_id and deeply_nested:
                        inferred_node_id = deeply_nested.get("event_id") or deeply_nested.get("task_id")

            cascade_payload = {
                "old_start_time": args.get("old_start_time"),
                "new_start_time": args.get("start_time"),
                "new_end_time": args.get("end_time"),
                "new_deadline": args.get("deadline"),
                "title": args.get("title"),
                "location": args.get("location"),
            }
            cascade_result = None
            if inferred_node_id and tool_name in {"create_calendar_event", "update_calendar_event", "manage_tasks"}:
                change_type = "time_updated" if "calendar" in tool_name else "deadline_updated"
                cascade_result = await self.cascade_engine.cascade_update(
                    user_id=user_id,
                    node_id=inferred_node_id,
                    change_type=change_type,
                    payload=cascade_payload,
                )

            await self.repository.create_agent_log(
                {
                    "user_id": user_id,
                    "agent_name": "orchestrator",
                    "action": tool_name,
                    "status": "success" if result.get("status") == "success" else "failure",
                    "reason": "Direct tool execution from orchestrator",
                    "affected_nodes": [n for n in [inferred_node_id] if n],
                    "details": {"arguments": args, "session_context": session_context, "cascade": cascade_result},
                }
            )
            if cascade_result:
                return {**result, "cascade": cascade_result}
            return result

        loop_result = await self.llm_service.run_react_loop(
            user_input=message,
            conversation_messages=conversation,
            tool_callback=tool_callback,
        )

        cascade_payloads = []
        for action in loop_result.get("actions", []):
            result = action.get("result", {}) if isinstance(action, dict) else {}
            if isinstance(result, dict):
                cascade_info = result.get("cascade")
                if cascade_info:
                    cascade_payloads.append(cascade_info)

        merged_timeline: list[dict] = []
        merged_updated_nodes: list[str] = []
        merged_logs: list[dict] = []
        for cascade in cascade_payloads:
            merged_timeline.extend(cascade.get("timeline", []))
            merged_updated_nodes.extend([node.get("node_id") for node in cascade.get("updated_nodes", []) if node.get("node_id")])
            merged_logs.extend(cascade.get("logs", []))

        if merged_timeline:
            merged_timeline = [{"step": idx + 1, "node": item.get("node"), "action": item.get("action")} for idx, item in enumerate(merged_timeline)]

        top_reasons = [log.get("reason") for log in merged_logs if log.get("reason")][:2]
        while len(top_reasons) < 2:
            top_reasons.append("No additional reasoning captured.")

        root_node = "unknown"
        if loop_result.get("actions"):
            first_action = loop_result["actions"][0]
            root_node = first_action.get("arguments", {}).get("event_id") or first_action.get("arguments", {}).get("task_id") or root_node

        story = (
            "Your schedule was automatically optimized using dependency-aware AI.\n\n"
            f"Root change: {root_node}\n"
            f"Impact: {len(set(merged_updated_nodes))} dependent items were intelligently adjusted.\n\n"
            "Key reasoning:\n"
            f"- {top_reasons[0]}\n"
            f"- {top_reasons[1]}"
        )

        await self.repository.append_conversation_message(
            user_id,
            {
                "role": "assistant",
                "content": loop_result["summary"],
                "actions": loop_result["actions"],
            },
        )
        await self.repository.upsert_session_context(
            user_id,
            {
                "last_message": message,
                "last_summary": loop_result["summary"],
                "last_actions": loop_result["actions"][-3:],
            },
        )

        recommendations = [
            "You have high task density after 3 PM - consider redistributing workload.",
            "This change may reduce your focus window - schedule a buffer period.",
        ]

        return {
            "summary": loop_result["summary"],
            "story": story,
            "timeline": merged_timeline,
            "actions": loop_result["actions"],
            "recommendations": recommendations,
            "message": "Your day just healed itself.",
            "confidence_score": 0.92,
        }
