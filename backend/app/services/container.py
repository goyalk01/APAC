from __future__ import annotations

from app.agents.tool_router import ToolRouter
from app.agents.calendar_agent import CalendarAgent
from app.agents.notes_agent import NotesAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.task_agent import TaskAgent
from app.core.config import get_settings
from app.db.firestore_repository import build_repository
from app.mcp_client.client import MCPToolClient
from app.services.cascade_engine import CascadeEngine
from app.services.dependency_engine import DependencyEngine
from app.services.llm_service import LLMService


class ServiceContainer:
    def __init__(self) -> None:
        settings = get_settings()
        repository = build_repository(
            enable_firestore=settings.enable_firestore,
            project=settings.google_cloud_project,
            database=settings.firestore_database,
        )

        self.repository = repository
        self.llm_service = LLMService()

        mcp_client = MCPToolClient(settings.mcp_server_url)
        self.mcp_client = mcp_client
        task_agent = TaskAgent(repository, mcp_client)
        calendar_agent = CalendarAgent(repository, mcp_client)
        notes_agent = NotesAgent(repository, mcp_client)
        tool_router = ToolRouter(task_agent=task_agent, calendar_agent=calendar_agent, notes_agent=notes_agent)
        dependency_engine = DependencyEngine(repository)
        cascade_engine = CascadeEngine(
            repository=repository,
            dependency_engine=dependency_engine,
            mcp_client=mcp_client,
            llm_service=self.llm_service,
        )

        self.dependency_engine = dependency_engine
        self.cascade_engine = cascade_engine

        self.orchestrator = OrchestratorAgent(
            repository=repository,
            llm_service=self.llm_service,
            tool_router=tool_router,
            cascade_engine=cascade_engine,
            dependency_engine=dependency_engine,
        )


container = ServiceContainer()
