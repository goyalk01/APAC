import os

from fastapi.testclient import TestClient

os.environ["ALLOW_LOCAL_FUNCTION_CALL_STUB"] = "true"

from app.main import app
from app.services.container import container


def test_auth_and_workflow_roundtrip():
    client = TestClient(app)

    async def fake_execute(user_id: str, message: str):
        return {
            "summary": f"Executed for {user_id}",
            "story": "test story",
            "timeline": [{"step": 1, "node": "task_1", "action": "manage_tasks"}],
            "actions": [{"tool": "create_note", "result": {"status": "success"}}],
            "recommendations": ["ok"],
            "message": "Your day just healed itself.",
            "confidence_score": 0.92,
        }

    container.orchestrator.execute = fake_execute

    token_resp = client.post(
        "/v1/auth/token",
        json={"user_id": "u-api", "email": "u@example.com", "role": "user"},
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    workflow_resp = client.post(
        "/v1/workflows/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Schedule meeting tomorrow and prepare notes"},
    )
    assert workflow_resp.status_code == 200
    payload = workflow_resp.json()
    assert "summary" in payload
    assert len(payload["actions"]) == 1
