import uuid
from contextvars import ContextVar

# Single source of truth for correlation ID in async context
_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    val = _correlation_id_var.get()
    return val if val else str(uuid.uuid4())


def set_correlation_id(cid: str) -> None:
    _correlation_id_var.set(cid)


def generate_correlation_id() -> str:
    cid = str(uuid.uuid4())
    set_correlation_id(cid)
    return cid
