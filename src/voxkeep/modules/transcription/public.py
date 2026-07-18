"""Public construction API for the transcription module."""

from __future__ import annotations

import queue
import threading

from voxkeep.modules.storage.public import StorageEvent
from voxkeep.modules.transcription import worker as _worker
from voxkeep.shared.config import AsrConfig
from voxkeep.shared.events import CaptureEvent, ProcessedFrame


def build_transcription_module(
    *,
    audio_queue: queue.Queue[ProcessedFrame],
    capture_queue: queue.Queue[CaptureEvent],
    storage_queue: queue.Queue[StorageEvent],
    stop_event: threading.Event,
    cfg: AsrConfig,
) -> _worker.TranscriptionWorker:
    """Build the configured ASR streaming worker."""
    return _worker.TranscriptionWorker(
        audio_queue=audio_queue,
        capture_queue=capture_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=cfg,
    )


__all__ = ["build_transcription_module"]
