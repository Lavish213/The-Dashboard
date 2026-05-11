class KarpathysError(Exception):
    """Base for all platform errors."""

    def __init__(self, message: str, code: str = "internal_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(KarpathysError):
    def __init__(self, resource: str, id: str) -> None:
        super().__init__(f"{resource} not found: {id}", code="not_found")
        self.resource = resource
        self.resource_id = id


class ValidationError(KarpathysError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, code="validation_error")
        self.field = field


class AuthenticationError(KarpathysError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="authentication_error")


class AuthorizationError(KarpathysError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, code="authorization_error")


class ConflictError(KarpathysError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="conflict")


class RateLimitError(KarpathysError):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, code="rate_limit_exceeded")


class WorkflowError(KarpathysError):
    def __init__(self, message: str, workflow_id: str | None = None) -> None:
        super().__init__(message, code="workflow_error")
        self.workflow_id = workflow_id


class ExternalServiceError(KarpathysError):
    def __init__(self, service: str, message: str) -> None:
        super().__init__(f"{service}: {message}", code="external_service_error")
        self.service = service
