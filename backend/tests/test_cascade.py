import pytest

from app.db.repositories import InMemoryRepository
from app.mcp_client.client import MCPToolClient
from app.services.cascade_engine import CascadeEngine
from app.services.dependency_engine import DependencyEngine


@pytest.mark.asyncio
async def test_dependency_creation_and_retrieval():
    repo = InMemoryRepository()
    dependency_engine = DependencyEngine(repo)

    created = await dependency_engine.add_dependency("event_123", "task_456", "blocks")
    dependents = await dependency_engine.get_dependents("event_123")
    dependencies = await dependency_engine.get_dependencies("task_456")

    assert created["parent_id"] == "event_123"
    assert len(dependents) == 1
    assert dependents[0]["child_id"] == "task_456"
    assert len(dependencies) == 1
    assert dependencies[0]["parent_id"] == "event_123"


@pytest.mark.asyncio
async def test_cascade_propagation_and_explainable_logging():
    async def fake_call_tool(self, tool_name, arguments):
        return {"status": "success", "result": {"tool": tool_name, "arguments": arguments}}

    MCPToolClient.call_tool = fake_call_tool

    repo = InMemoryRepository()
    dependency_engine = DependencyEngine(repo)
    await dependency_engine.add_dependency("event_123", "task_456", "blocks")

    mcp_client = MCPToolClient("http://localhost:9000")
    cascade_engine = CascadeEngine(repository=repo, dependency_engine=dependency_engine, mcp_client=mcp_client)

    result = await cascade_engine.cascade_update(
        user_id="u1",
        node_id="event_123",
        change_type="time_updated",
        payload={
            "old_start_time": "2026-04-03T10:00:00+00:00",
            "new_start_time": "2026-04-03T15:00:00+00:00",
        },
    )

    assert result["updated_nodes"]
    assert any(node["node_id"] == "task_456" for node in result["updated_nodes"])

    logs = await repo.list_agent_logs("u1")
    assert logs
    cascade_log = logs[0]
    assert "reason" in cascade_log
    assert "event_123" in cascade_log["reason"]
    assert cascade_log.get("affected_nodes") == ["event_123", "task_456"]
