import pytest

from app.agents.tool_router import ToolRouter
from app.agents.calendar_agent import CalendarAgent
from app.agents.notes_agent import NotesAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.task_agent import TaskAgent
from app.db.repositories import InMemoryRepository
from app.mcp_client.client import MCPToolClient
from app.services.cascade_engine import CascadeEngine
from app.services.dependency_engine import DependencyEngine
from app.services.llm_service import LLMService


@pytest.mark.asyncio
async def test_orchestrator_executes_multi_agent_workflow():
    class FakeLLMService:
        async def run_react_loop(self, user_input, conversation_messages, tool_callback):
            first = await tool_callback(
                "create_calendar_event",
                {
                    "title": "Team sync",
                    "start_time": "2026-04-03T10:00:00+00:00",
                    "end_time": "2026-04-03T11:00:00+00:00",
                },
            )
            second = await tool_callback("create_note", {"content": f"Note: {user_input}", "tags": ["test"]})
            return {
                "summary": "done",
                "actions": [
                    {"tool": "create_calendar_event", "result": first},
                    {"tool": "create_note", "result": second},
                ],
            }

    async def fake_call_tool(self, tool_name, arguments):
        return {"status": "success", "result": {"tool": tool_name, "arguments": arguments}}

    MCPToolClient.call_tool = fake_call_tool
    repo = InMemoryRepository()
    mcp_client = MCPToolClient("http://localhost:9000")
    tool_router = ToolRouter(
        task_agent=TaskAgent(repo, mcp_client),
        calendar_agent=CalendarAgent(repo, mcp_client),
        notes_agent=NotesAgent(repo, mcp_client),
    )
    dependency_engine = DependencyEngine(repo)

    class FakeCascadeLLMService:
        async def generate_structured_output(self, prompt, context):
            return {
                "start_time": "2026-04-03T15:00:00+00:00",
                "end_time": "2026-04-03T16:00:00+00:00",
                "reason": "test",
            }

    cascade_engine = CascadeEngine(
        repository=repo,
        dependency_engine=dependency_engine,
        mcp_client=mcp_client,
        llm_service=FakeCascadeLLMService(),
    )

    orchestrator = OrchestratorAgent(
        repository=repo,
        llm_service=FakeLLMService(),
        tool_router=tool_router,
        cascade_engine=cascade_engine,
        dependency_engine=dependency_engine,
    )

    result = await orchestrator.execute("u1", "Schedule meeting tomorrow and prepare notes")

    assert "summary" in result
    assert len(result["actions"]) >= 2
    assert len(await repo.list_events("u1")) == 1
    assert len(await repo.list_notes("u1")) == 1
