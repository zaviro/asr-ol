"""Public entrypoints for the transcription module."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import queue
import threading
from typing import Callable, Protocol

from voxkeep.modules.transcription.contracts import TranscriptionBackendEvent, TranscriptionEngine
from voxkeep.modules.transcription.infrastructure.engine_factory import build_asr_engine
from voxkeep.shared.config import AsrConfig, StorageConfig
from voxkeep.shared.events import AsrFinalEvent, ProcessedFrame, StorageRecord
from voxkeep.shared.queue_utils import put_nowait_or_drop

logger = logging.getLogger(__name__)
_AUDIO_QUEUE_GET_TIMEOUT_S = 0.05
_QUEUE_GET_TIMEOUT_S = 0.1


def _normalize_backend_event(event: TranscriptionBackendEvent) -> AsrFinalEvent:
    """Normalize one backend transcript event into the shared ASR event type."""
    return AsrFinalEvent(
        segment_id=event.segment_id,
        text=event.text,
        start_ts=event.start_ts,
        end_ts=event.end_ts,
        is_final=event.is_final,
    )


class TranscriptionModule(Protocol):
    """Public API exposed by the transcription module."""

    def start(self) -> None:
        """Start module resources."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop module resources."""
        raise NotImplementedError

    def submit_audio(self, frame: ProcessedFrame) -> None:
        """Submit one audio frame into the transcription pipeline."""
        raise NotImplementedError

    def subscribe_transcript_finalized(self, handler: Callable[[AsrFinalEvent], None]) -> None:
        """Subscribe to final transcript events."""
        raise NotImplementedError

    def join(self, timeout: float | None = None) -> None:
        """Join module resources."""
        raise NotImplementedError

    def is_alive(self) -> bool:
        """Report whether module resources are alive."""
        raise NotImplementedError


class WorkerTranscriptionModule:
    """Transcription module that streams audio to ASR backend and fans out results."""

    def __init__(
        self,
        *,
        capture_queue: queue.Queue[AsrFinalEvent],
        storage_queue: queue.Queue[StorageRecord],
        stop_event: threading.Event,
        asr_cfg: AsrConfig,
        storage_cfg: StorageConfig,
        in_queue: queue.Queue[ProcessedFrame] | None = None,
        _engine: TranscriptionEngine | None = None,
    ) -> None:
        """Create transcription module dependencies and engine."""
        self._in_queue = in_queue or queue.Queue(maxsize=asr_cfg.max_queue_size)
        self._capture_queue = capture_queue
        self._storage_queue = storage_queue
        self._stop_event = stop_event
        self._handlers: list[Callable[[AsrFinalEvent], None]] = []
        self._thread: threading.Thread | None = None

        self._engine = (
            _engine if _engine is not None else build_asr_engine(cfg=asr_cfg, stop_event=stop_event)
        )
        self._backend_final_queue: queue.Queue[TranscriptionBackendEvent] = self._engine.final_queue
        self._store_final_only = storage_cfg.store_final_only

    def start(self) -> None:
        """Start engine resources and the background worker thread."""
        if self._thread is not None:
            return
        self._engine.start()
        self._thread = threading.Thread(target=self._run, name="transcription_module", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Expose a symmetric lifecycle hook for the runtime module."""
        self._stop_event.set()

    def submit_audio(self, frame: ProcessedFrame) -> None:
        """Submit one audio frame into the transcription pipeline."""
        put_nowait_or_drop(
            self._in_queue,
            frame,
            logger=logger,
            warning=f"transcription input queue full; dropping frame_id={frame.frame_id}",
        )

    def subscribe_transcript_finalized(self, handler: Callable[[AsrFinalEvent], None]) -> None:
        """Subscribe to final transcript events."""
        self._handlers.append(handler)

    def join(self, timeout: float | None = None) -> None:
        """Join worker thread and engine."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        join_fn = getattr(self._engine, "join", None)
        if callable(join_fn):
            join_fn(timeout=timeout)

    def is_alive(self) -> bool:
        """Report whether the worker thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        logger.info("transcription module started")
        while (
            not self._stop_event.is_set()
            or not self._in_queue.empty()
            or not self._backend_final_queue.empty()
        ):
            self._submit_audio_once()
            self._drain_final_events()
        self._engine.close()
        self._drain_final_events()
        logger.info("transcription module stopped")

    def _submit_audio_once(self) -> None:
        try:
            frame = self._in_queue.get(timeout=_AUDIO_QUEUE_GET_TIMEOUT_S)
        except queue.Empty:
            return
        self._engine.submit_frame(frame)

    def _drain_final_events(self) -> None:
        while True:
            try:
                event = self._backend_final_queue.get_nowait()
            except queue.Empty:
                return

            normalized_event = _normalize_backend_event(event)
            if not normalized_event.is_final:
                continue
            self._fanout_event(normalized_event)
            record = StorageRecord(
                source="stream",
                text=normalized_event.text,
                start_ts=normalized_event.start_ts,
                end_ts=normalized_event.end_ts,
                is_final=normalized_event.is_final,
                created_at=datetime.now(tz=timezone.utc).isoformat(),
            )
            self._put_maybe_drop(self._storage_queue, record, "storage")

    def _fanout_event(self, event: AsrFinalEvent) -> None:
        self._put_maybe_drop(self._capture_queue, event, "capture")
        for handler in self._handlers:
            handler(event)

    @staticmethod
    def _put_maybe_drop(q: queue.Queue, event: object, name: str) -> None:
        put_nowait_or_drop(
            q, event, logger=logger, warning=f"queue full: dropping event from {name}"
        )


def build_transcription_module(
    *,
    capture_queue: queue.Queue[AsrFinalEvent],
    storage_queue: queue.Queue[StorageRecord],
    stop_event: threading.Event,
    asr_cfg: AsrConfig,
    storage_cfg: StorageConfig,
    in_queue: queue.Queue[ProcessedFrame] | None = None,
) -> TranscriptionModule:
    """Build the transcription module public entrypoint."""
    return WorkerTranscriptionModule(
        capture_queue=capture_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        asr_cfg=asr_cfg,
        storage_cfg=storage_cfg,
        in_queue=in_queue,
    )


__all__ = ["TranscriptionModule", "WorkerTranscriptionModule", "build_transcription_module"]
