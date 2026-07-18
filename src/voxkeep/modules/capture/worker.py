"""Queue-driven wake-to-command capture orchestration."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import logging
import queue
import threading
import time

from voxkeep.modules.capture.application.transcript_extractor import (
    InMemoryTranscriptExtractor,
    TranscriptExtractor,
)
from voxkeep.modules.capture.domain.capture_fsm import CaptureFSM, CaptureState, CaptureWindow
from voxkeep.modules.storage.public import StorageEvent
from voxkeep.shared.config import CaptureConfig
from voxkeep.shared.events import (
    AsrFinalEvent,
    CaptureCommand,
    CaptureEvent,
    VadEvent,
    WakeEvent,
)
from voxkeep.shared.queue_utils import put_nowait_or_drop

logger = logging.getLogger(__name__)

_EVENT_GET_TIMEOUT_S = 0.05
_FINAL_TRANSCRIPT_GRACE_S = 1.0
_VAD_HISTORY_SIZE = 64


@dataclass(slots=True)
class _PendingCapture:
    window: CaptureWindow
    deadline: float


class CaptureWorker:
    """Turn wake, VAD, and final ASR events into one capture command."""

    def __init__(
        self,
        *,
        event_queue: queue.Queue[CaptureEvent],
        command_queue: queue.Queue[CaptureCommand],
        storage_queue: queue.Queue[StorageEvent],
        stop_event: threading.Event,
        cfg: CaptureConfig,
        _fsm: CaptureFSM | None = None,
        _transcript_extractor: TranscriptExtractor | None = None,
    ) -> None:
        """Initialize capture coordination, routing, and transcript extraction."""
        self._event_queue = event_queue
        self._command_queue = command_queue
        self._storage_queue = storage_queue
        self._stop_event = stop_event
        self._thread: threading.Thread | None = None
        self._fsm = _fsm or CaptureFSM(
            pre_roll_ms=cfg.pre_roll_ms,
            armed_timeout_ms=cfg.armed_timeout_ms,
        )
        self._extractor = _transcript_extractor or InMemoryTranscriptExtractor()
        self._action_by_keyword = {rule.keyword: rule.action for rule in cfg.enabled_wake_rules}
        self._pending: list[_PendingCapture] = []
        self._vad_history: deque[VadEvent] = deque(maxlen=_VAD_HISTORY_SIZE)

    def start(self) -> None:
        """Start the capture worker once."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="capture_worker", daemon=True)
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        """Wait for pending events and captures to drain."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        """Report whether the capture thread is running."""
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        logger.info("capture worker started")
        while not self._stop_event.is_set() or not self._event_queue.empty() or self._pending:
            try:
                event = self._event_queue.get(timeout=_EVENT_GET_TIMEOUT_S)
            except queue.Empty:
                event = None

            if event is not None:
                self._handle(event)
            self._fsm.tick()
            self._flush_pending()
        logger.info("capture worker stopped")

    def _handle(self, event: CaptureEvent) -> None:
        if isinstance(event, WakeEvent):
            was_idle = self._fsm.state == CaptureState.IDLE
            self._fsm.on_wake(event)
            if was_idle:
                self._replay_vad_after_wake(event)
            return
        if isinstance(event, AsrFinalEvent):
            self._extractor.on_asr_final(event)
            return
        if isinstance(event, VadEvent):
            self._handle_vad(event, remember=True)

    def _replay_vad_after_wake(self, wake: WakeEvent) -> None:
        """Recover VAD transitions that arrived before a slower wake producer."""
        ordered = sorted(self._vad_history, key=lambda event: event.ts)
        earlier = [event for event in ordered if event.ts < wake.ts]
        later = [event for event in ordered if event.ts >= wake.ts]

        # A wake word can be recognized while VAD is already inside the same
        # utterance. Start the capture at the wake timestamp in that case.
        if earlier and earlier[-1].event_type == "speech_start":
            self._handle_vad(
                VadEvent(ts=wake.ts, event_type="speech_start", score=earlier[-1].score),
                remember=False,
            )

        for event in later:
            self._handle_vad(event, remember=False)

    def _handle_vad(self, event: VadEvent, *, remember: bool) -> None:
        if remember:
            self._vad_history.append(event)
        window = self._fsm.on_vad(event)
        if window is not None and not self._emit_if_ready(window):
            self._pending.append(
                _PendingCapture(
                    window=window,
                    deadline=time.monotonic() + _FINAL_TRANSCRIPT_GRACE_S,
                )
            )

    def _flush_pending(self) -> None:
        if not self._pending:
            return
        now = time.monotonic()
        remaining: list[_PendingCapture] = []
        for pending in self._pending:
            if self._emit_if_ready(pending.window):
                continue
            if now >= pending.deadline:
                logger.info(
                    "capture empty session_id=%s keyword=%s",
                    pending.window.session_id,
                    pending.window.keyword,
                )
                continue
            remaining.append(pending)
        self._pending = remaining

    def _emit_if_ready(self, window: CaptureWindow) -> bool:
        text = self._extractor.extract(start_ts=window.start_ts, end_ts=window.end_ts)
        if not text:
            return False

        command = CaptureCommand(
            session_id=window.session_id,
            keyword=window.keyword,
            action=self._action_by_keyword.get(window.keyword, "inject_text"),
            text=text,
            start_ts=window.start_ts,
            end_ts=window.end_ts,
        )
        if not put_nowait_or_drop(
            self._command_queue,
            command,
            logger=logger,
            warning=f"capture command queue full; dropping session_id={command.session_id}",
        ):
            return True

        logger.info(
            "capture finalized session_id=%s keyword=%s action=%s text=%s",
            command.session_id,
            command.keyword,
            command.action,
            command.text,
        )
        put_nowait_or_drop(
            self._storage_queue,
            command,
            logger=logger,
            warning=f"storage queue full; dropping capture session_id={command.session_id}",
        )
        return True
