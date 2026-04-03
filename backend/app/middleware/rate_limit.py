from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.access_log: dict[str, deque[datetime]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=1)

        records = self.access_log[client_ip]
        while records and records[0] < cutoff:
            records.popleft()

        if len(records) >= self.requests_per_minute:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        records.append(now)
        return await call_next(request)
