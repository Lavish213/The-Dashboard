"""
Startup secret validation — fail-fast on misconfiguration.

Called once at startup. Raises RuntimeError on any violation in production.
Logs warnings in development so dev loop is not blocked.
"""
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

_MIN_SECRET_KEY_LENGTH = 32
_INSECURE_DEFAULTS = {
    "changeme-in-production-use-long-random-string",
    "changeme-use-a-long-random-string-in-production",
    "dev-secret-key-change-in-production-at-least-32-chars",
    "secret",
    "password",
    "changeme",
}


def validate_secrets(settings) -> None:  # type: ignore[annotation-unchecked]
    """
    Validate all secret-bearing settings.
    Production: raises RuntimeError on any failure.
    Development: logs warnings only.
    """
    errors: list[str] = []

    # SECRET_KEY
    if settings.secret_key in _INSECURE_DEFAULTS:
        errors.append(
            "SECRET_KEY is a known-insecure default. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    elif len(settings.secret_key) < _MIN_SECRET_KEY_LENGTH:
        errors.append(
            f"SECRET_KEY must be at least {_MIN_SECRET_KEY_LENGTH} characters "
            f"(current: {len(settings.secret_key)})"
        )

    if settings.is_production:
        # DATABASE_URL must not point to localhost
        if "localhost" in settings.database_url or "127.0.0.1" in settings.database_url:
            errors.append("DATABASE_URL points to localhost in production.")

        # REDIS_URL must not point to localhost
        if "localhost" in settings.redis_url or "127.0.0.1" in settings.redis_url:
            errors.append("REDIS_URL points to localhost in production.")

        # CORS must not be wildcard
        if "*" in str(settings.cors_origins):
            errors.append("CORS_ORIGINS must not contain wildcard (*) in production.")

    if errors:
        msg = "Startup secret validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        if settings.is_production:
            raise RuntimeError(msg)
        for error in errors:
            logger.warning("security.secrets.insecure_config", detail=error)
    else:
        logger.info("security.secrets.validated", env=settings.app_env)
