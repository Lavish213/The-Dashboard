"""
Startup secret validation — fail-fast on misconfiguration.

Called once at startup. Raises RuntimeError on any violation.
Does not read .env itself — delegates to Settings (already loaded).
"""
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

_MIN_SECRET_KEY_LENGTH = 32
_INSECURE_DEFAULTS = {
    "changeme-in-production-use-long-random-string",
    "secret",
    "password",
    "changeme",
}


def validate_secrets(settings) -> None:  # type: ignore[annotation-unchecked]
    """
    Validate all secret-bearing settings.
    Raises RuntimeError with a descriptive message on failure.
    Only enforced in production by default; warns loudly in development.
    """
    errors: list[str] = []

    # SECRET_KEY checks
    if settings.secret_key in _INSECURE_DEFAULTS:
        errors.append(
            "SECRET_KEY is a known-insecure default value. "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    elif len(settings.secret_key) < _MIN_SECRET_KEY_LENGTH:
        errors.append(
            f"SECRET_KEY must be at least {_MIN_SECRET_KEY_LENGTH} characters. "
            f"Current length: {len(settings.secret_key)}"
        )

    # DATABASE_URL checks
    if "localhost" in settings.database_url and settings.is_production:
        errors.append("DATABASE_URL points to localhost in production environment.")

    if errors:
        if settings.is_production:
            raise RuntimeError(
                "Startup secret validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )
        else:
            for error in errors:
                logger.warning("security.secrets.insecure_config", detail=error)
    else:
        logger.info("security.secrets.validated", env=settings.app_env)
