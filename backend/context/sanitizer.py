"""
ContextItemSanitizer — content sanitization before context injection.

Detects and blocks:
  - Secret patterns: API keys, bearer tokens, private keys, passwords in content
  - Oversized items: content exceeding max_content_chars
  - Null/empty content that would corrupt context windows

Fail-closed: raises ContextSanitizationError on any violation.
Pure: no I/O.

sanitize(item) → ContextItem (passthrough if clean)
sanitize_batch(items) → list[ContextItem] (all-or-nothing: raises on first hit)
"""
from __future__ import annotations

import re

from context.contracts import ContextItem
from context.exceptions import ContextSanitizationError

# Default max content length to prevent oversized injection
_DEFAULT_MAX_CONTENT_CHARS = 32_768  # 32K chars ~ 8K tokens

# Patterns that indicate secret content that must not be injected
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("api_key", re.compile(r"\b(?:api[_-]?key|apikey)\s*[:=]\s*\S{8,}", re.IGNORECASE)),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("password_field", re.compile(r"\b(?:password|passwd|secret|token)\s*[:=]\s*\S{4,}", re.IGNORECASE)),
    ("jwt_token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
]


class ContextItemSanitizer:
    """
    Stateless content sanitizer.

    sanitize(item) — raises ContextSanitizationError or returns item unchanged.
    sanitize_batch(items) — raises on first violation, else returns full list.
    """

    def __init__(self, max_content_chars: int = _DEFAULT_MAX_CONTENT_CHARS) -> None:
        self._max_content_chars = max_content_chars

    def sanitize(self, item: ContextItem) -> ContextItem:
        """
        Validate and return item unchanged if clean.
        Raises ContextSanitizationError on violation.
        """
        if not item.content or not item.content.strip():
            raise ContextSanitizationError(
                reason="empty or whitespace-only content",
                field="content",
            )

        if len(item.content) > self._max_content_chars:
            raise ContextSanitizationError(
                reason=f"content too large: {len(item.content)} > {self._max_content_chars}",
                field="content",
            )

        for pattern_name, pattern in _SECRET_PATTERNS:
            if pattern.search(item.content):
                raise ContextSanitizationError(
                    reason=f"secret pattern detected: {pattern_name}",
                    field="content",
                )

        return item

    def sanitize_batch(self, items: list[ContextItem]) -> list[ContextItem]:
        """
        Sanitize all items. Raises on first violation.
        Returns full list if all clean.
        """
        for item in items:
            self.sanitize(item)
        return items

    def is_clean(self, item: ContextItem) -> bool:
        """Non-raising check. Returns True if item passes all sanitization."""
        try:
            self.sanitize(item)
            return True
        except ContextSanitizationError:
            return False
