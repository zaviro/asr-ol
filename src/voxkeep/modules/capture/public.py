"""Public entrypoints for the capture module."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import queue
import threading
import time
from typing import Callable, Protocol

from voxkeep.modules.capture.application.transcript_extractor import (
    InMemoryTranscriptExtractor,
    TranscriptExtractor,
)
from voxkeep.modules.capture.domain.capture_fsm import CaptureFSM, CaptureWindow
from voxkeep.modules.capture.infrastructure.openwakeword_worker import OpenWakeWordWorker
from voxkeep.modules.capture.infrastructure.silero_worker import SileroVadWorker
from voxkeep.shared.config import CaptureConfig
from voxkeep.shared.events import (
    AsrFinalEvent,
    CaptureCommand,
    ProcessedFrame,
    StorageRecord,
    VadEvent,
    WakeEvent,
)
from voxkeep.shared.queue_utils import put_nowait_or_drop

logger = logging.getLogger(__name__)
_IDLE_SLEEP_S = 0.01
_QUEUE_GET_TIMEOUT_S = 0.1


class DetectionWorker(Protocol):
    """Minimal lifecycle contract for capture-side detection workers."""

    def start(self) -> None:
        raise NotImplementedError

    def join(self, timeout: float | None = None) -> None:
        raise NotImplementedError

    def is_alive(self) -> bool:
        raise NotImplementedError


class CaptureModule(Protocol):
    """Public API exposed by the capture module."""

    def start(self) -> None:
        """Start module resources."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop module resources."""
        raise NotImplementedError

    def accept_wake(self, event: WakeEvent) -> None:
        """Accept one wake detection event."""
        raise NotImplementedError

    def accept_vad(self, event: VadEvent) -> None:
        """Accept one VAD boundary event."""
        raise NotImplementedError

    def accept_transcript(self, event: AsrFinalEvent) -> None:
        """Accept one transcript event."""
        raise NotImplementedError

    def subscribe_capture_completed(self, handler: Callable[[CaptureCommand], None]) -> None:
        """Subscribe to capture completion events."""
        raise NotImplementedError

    def join(self, timeout: float | None = None) -> None:
        """Join module resources."""
        raise NotImplementedError

    def is_alive(self) -> bool:
        """Report whether module resources are alive."""
        raise NotImplementedError


class WorkerCaptureModule:
    """Capture module that runs wake-triggered capture orchestration in a background thread."""

    def __init__(
        self,
        *,
        downstream_queue: queue.Queue[CaptureCommand],
        storage_queue: queue.Queue[StorageRecord],
        stop_event: threading.Event,
        cfg: CaptureConfig,
        wake_queue: queue.Queue[WakeEvent] | None = None,
        vad_queue: queue.Queue[VadEvent] | None = None,
        asr_queue: queue.Queue[AsrFinalEvent] | None = None,
        _fsm: CaptureFSM | None = None,
        _transcript_extractor: TranscriptExtractor | None = None,
    ) -> None:
        """Create capture module dependencies and routing rules."""
        self._wake_queue = wake_queue or queue.Queue(maxsize=cfg.max_queue_size)
        self._vad_queue = vad_queue or queue.Queue(maxsize=cfg.max_queue_size)
        self._asr_queue = asr_queue or queue.Queue(maxsize=cfg.max_queue_size)
        self._downstream_queue = downstream_queue
        self._storage_queue = storage_queue
        self._stop_event = stop_event
        self._handlers: list[Callable[[CaptureCommand], None]] = []
        self._thread: threading.Thread | None = None

        self._fsm = (
            _fsm
            if _fsm is not None
            else CaptureFSM(pre_roll_ms=cfg.pre_roll_ms, armed_timeout_ms=cfg.armed_timeout_ms)
        )
        self._extractor = (
            _transcript_extractor
            if _transcript_extractor is not None
            else InMemoryTranscriptExtractor()
        )
        self._action_by_keyword = {rule.keyword: rule.action for rule in cfg.enabled_wake_rules}
        self._default_action = "inject_text"

    def start(self) -> None:
        """Start the capture module background thread."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="capture_module", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Expose a symmetric lifecycle hook for the runtime module."""
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        """Join the background thread."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        """Report whether the background thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def accept_wake(self, event: WakeEvent) -> None:
        """Accept one wake detection event."""
        put_nowait_or_drop(self._wake_queue, event, logger=logger)

    def accept_vad(self, event: VadEvent) -> None:
        """Accept one VAD boundary event."""
        put_nowait_or_drop(self._vad_queue, event, logger=logger)

    def accept_transcript(self, event: AsrFinalEvent) -> None:
        """Accept one transcript event."""
        put_nowait_or_drop(self._asr_queue, event, logger=logger)

    def subscribe_capture_completed(self, handler: Callable[[CaptureCommand], None]) -> None:
        """Subscribe to capture completion events."""
        self._handlers.append(handler)

    def _run(self) -> None:
        logger.info("capture module started")
        while (
            not self._stop_event.is_set()
            or not self._wake_queue.empty()
            or not self._vad_queue.empty()
            or not self._asr_queue.empty()
        ):
            had_event = self._consume_once()
            self._fsm.tick()
            if not had_event:
                time.sleep(_IDLE_SLEEP_S)
        logger.info("capture module stopped")

    def _consume_once(self) -> bool:
        handled = False

        try:
            wake_event = self._wake_queue.get_nowait()
            self._fsm.on_wake(wake_event)
            handled = True
        except queue.Empty:
            pass

        try:
            asr_event = self._asr_queue.get_nowait()
            self._extractor.on_asr_final(asr_event)
            handled = True
        except queue.Empty:
            pass

        try:
            vad_event = self._vad_queue.get_nowait()
            window = self._fsm.on_vad(vad_event)
            if window is not None:
                self._emit_capture(window)
            handled = True
        except queue.Empty:
            pass

        return handled

    def _emit_capture(self, window: CaptureWindow) -> None:
        start_ts = window.start_ts
        end_ts = window.end_ts
        keyword = window.keyword
        session_id = window.session_id
        text = self._extractor.extract(start_ts=start_ts, end_ts=end_ts)
        if not text:
            logger.info("capture empty session_id=%s keyword=%s", session_id, keyword)
            return

        action = self._action_by_keyword.get(keyword, self._default_action)
        command = CaptureCommand(
            session_id=session_id,
            keyword=keyword,
            action=action,
            text=text,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        if put_nowait_or_drop(
            self._downstream_queue,
            command,
            logger=logger,
            warning=f"capture out queue full; dropping session_id={command.session_id}",
        ):
            logger.info(
                "capture finalized session_id=%s keyword=%s action=%s text=%s",
                command.session_id,
                command.keyword,
                command.action,
                command.text,
            )
        else:
            return

        for handler in self._handlers:
            handler(command)

        record = StorageRecord(
            source="capture",
            text=command.text,
            start_ts=command.start_ts,
            end_ts=command.end_ts,
            is_final=True,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        put_nowait_or_drop(
            self._storage_queue,
            record,
            logger=logger,
            warning=f"storage queue full; dropping capture storage session_id={command.session_id}",
        )


def build_capture_module(
    *,
    downstream_queue: queue.Queue[CaptureCommand],
    storage_queue: queue.Queue[StorageRecord],
    stop_event: threading.Event,
    cfg: CaptureConfig,
    wake_queue: queue.Queue[WakeEvent] | None = None,
    vad_queue: queue.Queue[VadEvent] | None = None,
    asr_queue: queue.Queue[AsrFinalEvent] | None = None,
) -> CaptureModule:
    """Build the capture module public entrypoint."""
    return WorkerCaptureModule(
        downstream_queue=downstream_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=cfg,
        wake_queue=wake_queue,
        vad_queue=vad_queue,
        asr_queue=asr_queue,
    )


def build_capture_detection_workers(
    *,
    in_queue: queue.Queue[ProcessedFrame],
    wake_out_queue: queue.Queue[WakeEvent],
    vad_out_queue: queue.Queue[VadEvent],
    stop_event: threading.Event,
    cfg: CaptureConfig,
) -> tuple[DetectionWorker, DetectionWorker]:
    """Build wake and VAD workers behind the capture module public API."""
    wake_worker = OpenWakeWordWorker(
        in_queue=in_queue,
        out_queue=wake_out_queue,
        stop_event=stop_event,
        rules=cfg.enabled_wake_rules,
    )
    vad_worker = SileroVadWorker(
        in_queue=in_queue,
        out_queue=vad_out_queue,
        stop_event=stop_event,
        speech_threshold=cfg.vad_speech_threshold,
        silence_ms=cfg.vad_silence_ms,
    )
    return wake_worker, vad_worker


__all__ = [
    "CaptureModule",
    "WorkerCaptureModule",
    "build_capture_detection_workers",
    "build_capture_module",
]
