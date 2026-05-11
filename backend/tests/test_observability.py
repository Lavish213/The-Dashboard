from observability.correlation import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from observability.logging import configure_logging, get_logger


def test_correlation_id_set_and_get():
    set_correlation_id("abc-123")
    assert get_correlation_id() == "abc-123"


def test_generate_correlation_id_is_uuid():
    import uuid
    cid = generate_correlation_id()
    uuid.UUID(cid)  # raises if invalid
    assert get_correlation_id() == cid


def test_correlation_id_default_is_valid_uuid():
    # Reset context (ContextVar default is "")
    # get_correlation_id() should return a generated UUID when empty
    set_correlation_id("")
    cid = get_correlation_id()
    import uuid
    uuid.UUID(cid)  # should not raise


def test_configure_logging_does_not_raise():
    configure_logging("development")
    configure_logging("production")


def test_get_logger_returns_logger():
    logger = get_logger("test")
    assert logger is not None
