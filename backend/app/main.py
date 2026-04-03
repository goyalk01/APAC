from typing import Annotated

from fastapi import Depends, FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.security import TokenUser, get_current_user
from app.core.logging_config import configure_logging
from app.middleware.rate_limit import SimpleRateLimitMiddleware
from app.models.schemas import CascadeTestRequest, CascadeTestResponse
from app.services.container import container

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)
app.add_middleware(SimpleRateLimitMiddleware, requests_per_minute=settings.rate_limit_requests_per_minute)
app.include_router(router, prefix=settings.api_prefix)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/cascade/test", response_model=CascadeTestResponse)
async def cascade_test_unversioned(
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
