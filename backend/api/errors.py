from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from api.responses import ErrorDetail, ErrorResponse, Meta
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    KarpathysError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from observability.correlation import get_correlation_id


def _error_response(
    code: str, message: str, status: int, field: str | None = None
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, field=field),
        meta=Meta(correlation_id=get_correlation_id()),
    )
    return JSONResponse(status_code=status, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return _error_response(exc.code, exc.message, 404)

    @app.exception_handler(AuthenticationError)
    async def auth_handler(request: Request, exc: AuthenticationError):
        return _error_response(exc.code, exc.message, 401)

    @app.exception_handler(AuthorizationError)
    async def authz_handler(request: Request, exc: AuthorizationError):
        return _error_response(exc.code, exc.message, 403)

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return _error_response(exc.code, exc.message, 409)

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError):
        return _error_response(exc.code, exc.message, 429)

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return _error_response(exc.code, exc.message, 422, exc.field)

    @app.exception_handler(KarpathysError)
    async def karpathys_handler(request: Request, exc: KarpathysError):
        return _error_response(exc.code, exc.message, 500)

    @app.exception_handler(PydanticValidationError)
    async def pydantic_handler(request: Request, exc: PydanticValidationError):
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        return _error_response("validation_error", first["msg"], 422, field)

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        return _error_response("internal_error", "An unexpected error occurred", 500)
