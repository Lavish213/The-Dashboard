"""
AI provider abstraction — protocol + test stub.

AIProvider is a structural Protocol (duck-typed). Any object with an
`execute(context) -> AITaskOutput` async method satisfies it.

NoOpProvider — deterministic test stub. Returns empty output instantly.
Registered automatically under AIProviderType.noop.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ai.contracts import AITaskOutput

if TYPE_CHECKING:
    from ai.context import AIExecutionContext


@runtime_checkable
class AIProvider(Protocol):
    """
    Structural protocol for AI provider backends.

    Implementations must be async-safe and idempotent for the same context.
    They must NOT persist state — the runtime owns all persistence.
    """

    async def execute(self, context: AIExecutionContext) -> AITaskOutput:
        """
        Execute the task described by `context`.
        Returns AITaskOutput on success; raises on failure.
        """
        ...


class NoOpProvider:
    """
    Test stub provider. Returns zero-token empty output.
    Safe to use in all unit/integration tests — never calls any external service.
    """

    async def execute(self, context: AIExecutionContext) -> AITaskOutput:
        return AITaskOutput(
            output={},
            tokens_used=0,
            model_name="noop",
        )


class ProviderRegistry:
    """
    In-process registry mapping AIProviderType → AIProvider instance.
    Callers register providers at startup; runtime looks them up by type.
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider_type: str, provider: AIProvider) -> None:
        self._providers[provider_type] = provider

    def get(self, provider_type: str) -> AIProvider | None:
        return self._providers.get(provider_type)

    def get_or_raise(self, provider_type: str) -> AIProvider:
        p = self.get(provider_type)
        if p is None:
            raise KeyError(f"No provider registered for type {provider_type!r}")
        return p


# Module-level singleton — populated at startup or in tests
provider_registry = ProviderRegistry()

# Register the noop stub immediately so tests work without setup
provider_registry.register("noop", NoOpProvider())
