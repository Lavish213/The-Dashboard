"""
Request metrics middleware — increments RuntimeMetrics counters per response.
Skips WebSocket upgrades and health check paths to avoid noise.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from observability.metrics import metrics

_SKIP_PATHS = frozenset({"/api/health", "/api/ready", "/api/metrics"})


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        response = await call_next(request)
        metrics.requests_total += 1

        if response.status_code >= 500:
            metrics.requests_5xx += 1
        elif response.status_code >= 400:
            metrics.requests_4xx += 1

        return response
