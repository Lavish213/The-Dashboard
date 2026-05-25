"""
Sophia runtime adapters — bridges to transcript and context layers.

Thin boundary translation — no business logic.
"""
from __future__ import annotations

from uuid import UUID

from sophia.contracts import SophiaContextInput


class SophiaContextAdapter:
    """
    Build context assembly input spec for a Sophia turn.
    Delegates actual assembly to the caller via ContextAssembler.
    Returns a typed input dict ready for ContextAssemblyInput.
    """

    @staticmethod
    def build_assembly_input(
        inp: SophiaContextInput,
    ) -> dict:
        """
        Return kwargs for ContextAssemblyInput construction.
        Caller constructs ContextAssemblyInput and calls assembler.assemble().
        """
        return {
            "assembly_key": f"sophia:{inp.session_id}:turn:{inp.turn_index}",
            "token_budget": inp.token_budget,
            "workflow_id": inp.workflow_id,
            "transcript_id": inp.transcript_id,
            "execution_id": inp.execution_id,
        }


class SophiaTranscriptAdapter:
    """
    Adapter for writing Sophia turn output to the transcript system.
    Translates turn output to transcript segment format.
    """

    @staticmethod
    def turn_to_segment_payload(
        session_id: UUID,
        turn_index: int,
        output_payload: dict,
    ) -> dict:
        """Build transcript segment input from turn output."""
        return {
            "source": "sophia",
            "session_id": str(session_id),
            "turn_index": turn_index,
            "text": output_payload.get("text", ""),
            "metadata": {
                k: v for k, v in output_payload.items() if k != "text"
            },
        }
