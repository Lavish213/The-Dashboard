"""
DuplicateEventError — raised when an event_id already exists in the store.
Callers should catch this and treat it as a no-op (at-least-once delivery).
"""
from __future__ import annotations


class DuplicateEventError(Exception):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"Duplicate event_id: {event_id!r}")
        self.event_id = event_id
