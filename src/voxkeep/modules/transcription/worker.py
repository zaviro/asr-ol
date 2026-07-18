"""Streaming transcription worker implementation."""

from __future__ import annotations

import logging
import queue
import threading

from voxkeep.modules.storage.public import StorageEvent
from voxkeep.modules.transcription.contracts import TranscriptionEngine
from voxkeep.modules.transcription.infrastructure.funasr_ws import FunAsrWsEngine
from voxkeep.shared.config import AsrConfig
from voxkeep.shared.events import CaptureEvent, ProcessedFrame
from voxkeep.shared.queue_utils import put_nowait_or_drop

logger = logging.getLogger(__name__)
_AUDIO_GET_TIMEOUT_S = 0.05


class TranscriptionWorker:
    """Stream audio to the configured ASR backend and publish final events."""

    def __init__(
        self,
        *,
        audio_queue: queue.Queue[ProcessedFrame],
        capture_queue: queue.Queue[CaptureEvent],
        storage_queue: queue.Queue[StorageEvent],
        stop_event: threading.Event,
        cfg: AsrConfig,
        _engine: TranscriptionEngine | None = None,
    ) -> None:
        """Initialize queue wiring and the configured ASR engine."""
        self._audio_queue = audio_queue
        self._capture_queue = capture_queue
        self._storage_queue = storage_queue
        self._stop_event = stop_event
        self._engine = _engine or FunAsrWsEngine(cfg=cfg)
        self._backend_events = self._engine.final_queue
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the ASR engine and transcription thread once."""
        if self._thread is not None:
            return
        self._engine.start()
        self._thread = threading.Thread(
            target=self._run,
            name="transcription_worker",
            daemon=True,
        )
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        """Wait for the worker thread and ASR engine to stop."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._engine.join(timeout=timeout)
        self._drain_final_events()

    def is_alive(self) -> bool:
        """Report whether the transcription thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        logger.info("transcription worker started")
        while (
            not self._stop_event.is_set()
            or not self._audio_queue.empty()
            or not self._backend_events.empty()
        ):
            self._submit_audio_once()
            self._drain_final_events()
        self._engine.close()
        self._drain_final_events()
        logger.info("transcription worker stopped")

    def _submit_audio_once(self) -> None:
        try:
            frame = self._audio_queue.get(timeout=_AUDIO_GET_TIMEOUT_S)
        except queue.Empty:
            return
        self._engine.submit_frame(frame)

    def _drain_final_events(self) -> None:
        while True:
            try:
                event = self._backend_events.get_nowait()
            except queue.Empty:
                return

            self._put(self._capture_queue, event, "capture")
            self._put(self._storage_queue, event, "storage")

    @staticmethod
    def _put(target: queue.Queue, event: object, name: str) -> None:
        put_nowait_or_drop(
            target,
            event,
            logger=logger,
            warning=f"{name} queue full; dropping final transcript",
        )
