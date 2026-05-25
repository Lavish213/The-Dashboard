"""
AI sandbox execution boundaries — scope constraints for AI executions.

SandboxPolicy — immutable set of boundaries for one execution context.
SandboxViolationError — raised when an operation breaches the sandbox.
SandboxGuard — enforces the policy at call sites.

Sandbox does NOT run code in an OS sandbox. It enforces application-level
constraints: which tools are allowed, whether external I/O is permitted,
token and time limits, and whether unsafe tools are blocked.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ai.registry import (
    AIToolRegistry,
    ai_tool_registry,
)


class SandboxViolationError(Exception):
    """Raised when an AI execution attempts an out-of-scope operation."""


@dataclass(frozen=True)
class SandboxPolicy:
    """
    Immutable boundary specification for one execution context.

    allowed_tool_ids — explicit allowlist. Empty = all tools permitted.
    deny_unsafe_tools — when True, tools with is_sandbox_safe=False are blocked.
    allow_external_io — when False, tools marked external are blocked (future).
    max_token_budget  — hard cap; overrides any per-task value if lower.
    max_timeout_seconds — hard cap on execution duration.
    """

    allowed_tool_ids: frozenset[str] = field(default_factory=frozenset)
    deny_unsafe_tools: bool = True
    allow_external_io: bool = False
    max_token_budget: int = 8192
    max_timeout_seconds: int = 60


class SandboxGuard:
    """
    Enforces a SandboxPolicy.

    check_tool()   — validate a tool call before execution.
    check_budget() — validate token budget against policy max.
    check_timeout()— validate timeout against policy max.
    """

    def __init__(
        self,
        policy: SandboxPolicy,
        registry: AIToolRegistry | None = None,
    ) -> None:
        self._policy = policy
        self._registry = registry or ai_tool_registry

    def check_tool(self, tool_id: str) -> None:
        """
        Raise SandboxViolationError if tool_id is not permitted under policy.
        """
        # Allowlist check (empty allowlist = all tools allowed)
        if self._policy.allowed_tool_ids and tool_id not in self._policy.allowed_tool_ids:
            raise SandboxViolationError(
                f"tool {tool_id!r} not in sandbox allowlist"
            )

        # Safety check
        if self._policy.deny_unsafe_tools:
            tool = self._registry.get(tool_id)
            if tool is not None and not tool.is_sandbox_safe:
                raise SandboxViolationError(
                    f"tool {tool_id!r} is not sandbox-safe (policy denies unsafe tools)"
                )

    def check_budget(self, requested_budget: int) -> None:
        """Raise SandboxViolationError if budget exceeds policy max."""
        if requested_budget > self._policy.max_token_budget:
            raise SandboxViolationError(
                f"token budget {requested_budget} exceeds sandbox max "
                f"{self._policy.max_token_budget}"
            )

    def check_timeout(self, requested_timeout: int) -> None:
        """Raise SandboxViolationError if timeout exceeds policy max."""
        if requested_timeout > self._policy.max_timeout_seconds:
            raise SandboxViolationError(
                f"timeout {requested_timeout}s exceeds sandbox max "
                f"{self._policy.max_timeout_seconds}s"
            )

    def effective_budget(self, requested_budget: int) -> int:
        """Return the lesser of requested_budget and policy max."""
        return min(requested_budget, self._policy.max_token_budget)

    def effective_timeout(self, requested_timeout: int) -> int:
        """Return the lesser of requested_timeout and policy max."""
        return min(requested_timeout, self._policy.max_timeout_seconds)


# Default permissive sandbox for non-restricted contexts (e.g. internal tooling)
PERMISSIVE_SANDBOX = SandboxPolicy(
    allowed_tool_ids=frozenset(),  # all tools
    deny_unsafe_tools=False,
    allow_external_io=True,
    max_token_budget=32768,
    max_timeout_seconds=300,
)

# Default restrictive sandbox for untrusted / approval-required contexts
RESTRICTED_SANDBOX = SandboxPolicy(
    allowed_tool_ids=frozenset(),  # caller must set allowlist
    deny_unsafe_tools=True,
    allow_external_io=False,
    max_token_budget=4096,
    max_timeout_seconds=30,
)
