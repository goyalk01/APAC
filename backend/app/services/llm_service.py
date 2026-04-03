from __future__ import annotations

from importlib import import_module
import json
from typing import Any

from app.core.config import get_settings
from app.services.function_registry import FUNCTION_SPECS


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_tools(self) -> list[Any]:
        generative_models = import_module("vertexai.generative_models")
        FunctionDeclaration = getattr(generative_models, "FunctionDeclaration")
        Tool = getattr(generative_models, "Tool")

        declarations = [
            FunctionDeclaration(
                name=spec.name,
                description=spec.description,
                parameters=spec.parameters,
            )
            for spec in FUNCTION_SPECS
        ]
        return [Tool(function_declarations=declarations)]

    async def run_react_loop(
        self,
        user_input: str,
        conversation_messages: list[dict[str, Any]],
        tool_callback,
    ) -> dict[str, Any]:
        if not self.settings.google_cloud_project and self.settings.allow_local_function_call_stub:
            first = await tool_callback(
                "create_calendar_event",
                {
                    "title": "Planned meeting",
                    "start_time": "2026-04-03T10:00:00+00:00",
                    "end_time": "2026-04-03T11:00:00+00:00",
                },
            )
            second = await tool_callback(
                "create_note",
                {
                    "content": f"Notes for: {user_input}",
                    "tags": ["auto"],
                },
            )
            return {
                "summary": "Workflow completed via local function-calling stub.",
                "actions": [
                    {"tool": "create_calendar_event", "arguments": {}, "result": first},
                    {"tool": "create_note", "arguments": {}, "result": second},
                ],
            }

        if not self.settings.google_cloud_project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Vertex AI function calling")

        vertexai = import_module("vertexai")
        generative_models = import_module("vertexai.generative_models")
        init = getattr(vertexai, "init")
        GenerativeModel = getattr(generative_models, "GenerativeModel")
        Part = getattr(generative_models, "Part")

        init(project=self.settings.google_cloud_project, location=self.settings.google_cloud_location)
        model = GenerativeModel(self.settings.vertex_model_name)
        tools = self._build_tools()

        system_prompt = (
            "You are a productivity orchestrator. Use function calling for every external action. "
            "Never fabricate tool results. You may call multiple functions over multiple turns. "
            "Return final concise summary after all required tool calls."
        )

        history_text = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in conversation_messages[-12:]])
        current_text = f"Conversation history:\n{history_text}\n\nUser request:\n{user_input}"

        actions: list[dict[str, Any]] = []

        for _ in range(self.settings.vertex_max_steps):
            response = model.generate_content([system_prompt, current_text], tools=tools)

            function_calls = []
            for candidate in getattr(response, "candidates", []) or []:
                content = getattr(candidate, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []) or []:
                    function_call = getattr(part, "function_call", None)
                    if function_call:
                        function_calls.append(function_call)

            if not function_calls:
                final_text = (response.text or "Completed workflow.").strip()
                return {"summary": final_text, "actions": actions}

            for call in function_calls:
                tool_name = call.name
                tool_args = dict(call.args)
                tool_result = await tool_callback(tool_name, tool_args)
                actions.append({"tool": tool_name, "arguments": tool_args, "result": tool_result})

                function_response_part = Part.from_function_response(
                    name=tool_name,
                    response={"result": tool_result},
                )
                follow_up = model.generate_content([system_prompt, current_text, function_response_part], tools=tools)
                current_text = (follow_up.text or current_text).strip()

        return {
            "summary": "Max reasoning steps reached. Partial workflow completed.",
            "actions": actions,
        }

    async def generate_structured_output(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.google_cloud_project and self.settings.allow_local_function_call_stub:
            return {
                "start_time": context.get("change_payload", {}).get("new_start_time"),
                "end_time": context.get("change_payload", {}).get("new_end_time"),
                "reason": "Local stub scheduling decision",
            }

        if not self.settings.google_cloud_project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Vertex AI structured output")

        vertexai = import_module("vertexai")
        generative_models = import_module("vertexai.generative_models")
        init = getattr(vertexai, "init")
        GenerativeModel = getattr(generative_models, "GenerativeModel")

        init(project=self.settings.google_cloud_project, location=self.settings.google_cloud_location)
        model = GenerativeModel(self.settings.vertex_model_name)

        instruction = (
            "Return only compact JSON with keys start_time, end_time, reason. "
            "Pick next non-conflicting slot based on schedule context. "
            f"Prompt: {prompt}\nContext: {json.dumps(context)}"
        )
        response = model.generate_content([instruction])
        text = (response.text or "{}").strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.replace("json", "", 1).strip()
        parsed = json.loads(text)
        return {
            "start_time": parsed.get("start_time"),
            "end_time": parsed.get("end_time"),
            "reason": parsed.get("reason", "LLM scheduling decision"),
        }
