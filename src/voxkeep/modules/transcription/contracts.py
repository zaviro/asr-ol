"""Internal engine contract for transcription backends."""

from __future__ import annotations

import queue
from typing import Protocol

from voxkeep.shared.events import AsrFinalEvent, ProcessedFrame


class TranscriptionEngine(Protocol):
    """Structural contract for transcription backends."""

    @property
    def final_queue(self) -> queue.Queue[AsrFinalEvent]:
        """Queue that receives normalized final transcript events."""
        raise NotImplementedError

    def start(self) -> None:
        """Start engine resources."""
        raise NotImplementedError

    def submit_frame(self, frame: ProcessedFrame) -> None:
        """Submit one processed audio frame."""
        raise NotImplementedError

    def close(self) -> None:
        """Stop engine resources."""
        raise NotImplementedError

    def join(self, timeout: float | None = None) -> None:
        """Join engine resources."""
        raise NotImplementedError


__all__ = ["TranscriptionEngine"]
