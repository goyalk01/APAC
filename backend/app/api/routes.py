from typing import Annotated
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.security import TokenUser, create_access_token, get_current_user, parse_token, require_roles
from app.models.schemas import (
    CascadeStreamEvent,
    CascadeTestRequest,
    CascadeTestResponse,
    DependencyModel,
    LoginRequest,
    UndoCascadeRequest,
    WorkflowRequest,
    WorkflowResponse,
)
from app.services.container import container
from app.utils.sanitization import sanitize_text

router = APIRouter()


@router.post("/auth/token")
async def issue_token(payload: LoginRequest) -> dict[str, str]:
    await container.repository.upsert_user(
        payload.user_id,
        {
            "email": payload.email,
            "role": payload.role,
        },
    )
    token = create_access_token(TokenUser(user_id=payload.user_id, email=payload.email, role=payload.role))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/workflows/execute", response_model=WorkflowResponse)
async def execute_workflow(
    body: WorkflowRequest,
    user: Annotated[TokenUser, Depends(get_current_user)],
) -> WorkflowResponse:
    sanitized = sanitize_text(body.message)
    result = await container.orchestrator.execute(user.user_id, sanitized)
    return WorkflowResponse(**result)


@router.get("/me/tasks")
async def my_tasks(user: Annotated[TokenUser, Depends(get_current_user)]) -> dict:
    tasks = await container.repository.list_tasks(user.user_id)
    return {"items": tasks}


@router.get("/me/events")
async def my_events(user: Annotated[TokenUser, Depends(get_current_user)]) -> dict:
    events = await container.repository.list_events(user.user_id)
    return {"items": events}


@router.get("/me/notes")
async def my_notes(user: Annotated[TokenUser, Depends(get_current_user)]) -> dict:
    notes = await container.repository.list_notes(user.user_id)
    return {"items": notes}


@router.get("/admin/agent-logs")
async def agent_logs(_user: Annotated[TokenUser, Depends(require_roles("admin"))]) -> dict:
    logs = await container.repository.list_agent_logs()
    return {"items": logs}


@router.post("/dependencies")
async def add_dependency(
    body: dict,
    user: Annotated[TokenUser, Depends(get_current_user)],
) -> dict:
    parent_id = body.get("parent_id")
    child_id = body.get("child_id")
    relation_type = body.get("type", "blocks")
    dependency = await container.dependency_engine.add_dependency(parent_id=parent_id, child_id=child_id, type=relation_type)
    await container.repository.create_agent_log(
        {
            "user_id": user.user_id,
            "agent_name": "dependency_engine",
            "action": "add_dependency",
            "status": "success",
            "reason": "User created dependency edge",
            "affected_nodes": [parent_id, child_id],
            "details": dependency,
        }
    )
    return dependency


@router.get("/dependencies", response_model=list[DependencyModel])
async def list_dependencies(_user: Annotated[TokenUser, Depends(get_current_user)]) -> list[DependencyModel]:
    deps = await container.repository.list_dependencies()
    return [DependencyModel(**dep) for dep in deps]


@router.post("/api/cascade/test", response_model=CascadeTestResponse)
async def cascade_test(
    body: CascadeTestRequest,
    user: Annotated[TokenUser, Depends(get_current_user)],
) -> CascadeTestResponse:
    result = await container.cascade_engine.cascade_update(
        user_id=user.user_id,
        node_id=body.node_id,
        change_type=body.change_type,
        payload=body.payload,
    )
    return CascadeTestResponse(**result)


@router.post("/cascade/undo")
async def undo_cascade(
    body: UndoCascadeRequest,
    user: Annotated[TokenUser, Depends(get_current_user)],
) -> dict:
    return await container.cascade_engine.undo_cascade(user.user_id, body.cascade_id)


@router.get("/workflows/stream")
async def stream_workflow_updates(
    node_id: str,
    change_type: str,
    access_token: str,
    payload_json: str | None = None,
):
    user = parse_token(access_token)
    payload = json.loads(payload_json) if payload_json else {}

    async def event_stream():
        async for event in container.cascade_engine.cascade_update_stream(
            user_id=user.user_id,
            node_id=node_id,
            change_type=change_type,
            payload=payload,
        ):
            envelope = CascadeStreamEvent(**event)
            yield f"event: update\ndata: {envelope.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
