"""
AI tool registry — in-process catalog of tools an AI may invoke.

AIToolDefinition — immutable descriptor for one tool.
AIToolRegistry   — register/lookup/enumerate tool definitions.

Tools flagged requires_approval=True must go through the approval gate
before execution proceeds. Tools with is_sandbox_safe=False are blocked
from sandbox execution contexts.

Module-level singleton: ai_tool_registry
"""
from __future__ import annotations

from dataclasses import dataclass

from models.enums import ApprovalType


@dataclass(frozen=True)
class AIToolDefinition:
    """Immutable descriptor for an AI-callable tool."""

    tool_id: str  # stable identifier, e.g. "send_sms", "fetch_lead_data"
    name: str  # human-readable
    description: str
    input_schema: dict  # JSON Schema describing required inputs
    requires_approval: bool = False
    approval_type: ApprovalType | None = None  # which approval type to create
    is_sandbox_safe: bool = True  # False = blocked in sandboxed contexts


class ToolNotFoundError(Exception):
    """Raised when looking up a tool_id that is not registered."""


class AIToolRegistry:
    """
    In-process registry. Not persisted — populate at application startup.
    Thread-safe for reads. Not designed for concurrent writes (register at startup only).
    """

    def __init__(self) -> None:
        self._tools: dict[str, AIToolDefinition] = {}

    def register(self, tool: AIToolDefinition) -> None:
        """Register a tool. Overwrites any existing registration for tool_id."""
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> AIToolDefinition | None:
        return self._tools.get(tool_id)

    def get_or_raise(self, tool_id: str) -> AIToolDefinition:
        tool = self.get(tool_id)
        if tool is None:
            raise ToolNotFoundError(f"Tool {tool_id!r} not registered")
        return tool

    def all(self) -> list[AIToolDefinition]:
        return list(self._tools.values())

    def requires_approval(self, tool_id: str) -> bool:
        tool = self.get(tool_id)
        return tool.requires_approval if tool is not None else False

    def is_sandbox_safe(self, tool_id: str) -> bool:
        tool = self.get(tool_id)
        return tool.is_sandbox_safe if tool is not None else False

    def unregister(self, tool_id: str) -> None:
        """Remove a tool. No-op if not registered. Useful in tests."""
        self._tools.pop(tool_id, None)


# Module-level singleton
ai_tool_registry = AIToolRegistry()
