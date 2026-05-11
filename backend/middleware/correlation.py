import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from observability.correlation import set_correlation_id


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Per-request middleware that:
    1. Reads X-Correlation-Id header (or generates a new UUID4 if absent)
    2. Sets it in the async context var so all log lines for this request carry it
    3. Injects X-Correlation-Id into the response headers
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = cid
        return response
