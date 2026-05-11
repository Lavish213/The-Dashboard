from core.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
    WorkflowError,
)


def test_not_found_error():
    exc = NotFoundError("lead", "abc-123")
    assert exc.code == "not_found"
    assert "lead" in exc.message
    assert "abc-123" in exc.message
    assert exc.resource == "lead"
    assert exc.resource_id == "abc-123"


def test_validation_error_with_field():
    exc = ValidationError("invalid email", field="email")
    assert exc.code == "validation_error"
    assert exc.field == "email"


def test_authentication_error_default():
    exc = AuthenticationError()
    assert exc.code == "authentication_error"
    assert "Authentication" in exc.message


def test_workflow_error():
    exc = WorkflowError("state machine broke", workflow_id="wf-999")
    assert exc.code == "workflow_error"
    assert exc.workflow_id == "wf-999"


def test_external_service_error():
    exc = ExternalServiceError("twilio", "connection refused")
    assert exc.code == "external_service_error"
    assert exc.service == "twilio"
    assert "twilio" in exc.message
