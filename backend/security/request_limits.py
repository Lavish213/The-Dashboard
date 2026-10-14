import hashlib
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.redis import get_redis

_SCRIPT = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"


class RequestLimits(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        limit = (
            10
            if path.endswith(("/auth/login", "/auth/refresh"))
            else 60
            if "instantdm" in path
            else 20
            if "/curator/" in path
            else None
        )
        if request.method == "OPTIONS" or limit is None:
            return await call_next(request)
        host = request.client.host if request.client else "unknown"
        bucket = int(time.time()) // 60
        key = (
            "request-limit:"
            + hashlib.sha256(f"{path}:{host}:{bucket}".encode()).hexdigest()
        )
        try:
            async for redis in get_redis():
                count = await redis.eval(_SCRIPT, 1, key, 120)
                if count > limit:
                    return JSONResponse(
                        {"detail": "Request limit reached"},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )
        except Exception:
            return JSONResponse(
                {"detail": "Request protection unavailable"}, status_code=503
            )
        return await call_next(request)
