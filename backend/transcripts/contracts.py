"""
Transcript session and streaming contracts — immutable input/output types.

All dataclasses are frozen. These types cross runtime boundaries without
carrying mutable state. Providers, callers, and tests all use these types.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from models.enums import (
    TranscriptSourceType,
    TranscriptStreamStatus,
    TranscriptStreamType,
)


@dataclass(frozen=True)
class TranscriptSessionInput:
    """Input to create a new transcript session."""

    source_type: TranscriptSourceType = TranscriptSourceType.call
    workflow_id: UUID | None = None
    call_id: UUID | None = None
    lead_id: UUID | None = None


@dataclass(frozen=True)
class StreamSessionInput:
    """Input to start a new streaming session within a transcript."""

    transcript_id: UUID
    stream_key: str  # caller-supplied idempotency key
    provider: str | None = None
    model_name: str | None = None


@dataclass(frozen=True)
class StreamChunkInput:
    """One committed chunk of transcript text from a stream."""

    stream_id: UUID
    speaker: str
    text: str
    stream_type: TranscriptStreamType = TranscriptStreamType.agent
    tokens_output: int = 0  # tokens consumed by this chunk


@dataclass(frozen=True)
class StreamResult:
    """Returned from stream lifecycle operations."""

    stream_id: UUID
    transcript_id: UUID
    stream_key: str
    status: TranscriptStreamStatus
    last_chunk_index: int | None
    tokens_input: int
    tokens_output: int


@dataclass(frozen=True)
class StreamChunkResult:
    """Result of committing one chunk."""

    stream_id: UUID
    chunk_id: UUID
    chunk_index: int
    tokens_output_cumulative: int


@dataclass(frozen=True)
class TokenUsage:
    """Aggregated token usage for a transcript or stream."""

    tokens_input: int
    tokens_output: int

    @property
    def total(self) -> int:
        return self.tokens_input + self.tokens_output


@dataclass(frozen=True)
class ReconstructionResult:
    """Result of stream reconstruction from persisted chunks."""

    transcript_id: UUID
    full_text: str
    chunk_count: int
    speakers: list[str]
    from_chunk_index: int
    to_chunk_index: int | None


@dataclass(frozen=True)
class CheckpointResult:
    """A single checkpoint record."""

    checkpoint_id: UUID
    transcript_id: UUID
    stream_id: UUID | None
    chunk_index: int
    label: str | None
    created_at: datetime


@dataclass(frozen=True)
class RetentionPolicy:
    """Immutable retention policy for a transcript."""

    archive_after_days: int | None = None   # archive after N days of inactivity
    delete_after_days: int | None = None    # soft-delete after N days
    requires_explicit_delete: bool = True   # block auto-delete unless False
