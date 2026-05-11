import structlog

_logger = structlog.get_logger("tracing")


def trace_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    correlation_id: str,
) -> None:
    _logger.info(
        "request_trace",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        correlation_id=correlation_id,
    )


def trace_db_query(
    query_name: str,
    duration_ms: float,
    success: bool,
) -> None:
    _logger.info(
        "db_query_trace",
        query_name=query_name,
        duration_ms=duration_ms,
        success=success,
    )
