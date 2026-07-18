"""Public builders for capture orchestration and detection."""

from __future__ import annotations

import queue
import threading

from voxkeep.modules.capture.infrastructure.openwakeword_worker import OpenWakeWordWorker
from voxkeep.modules.capture.infrastructure.silero_worker import SileroVadWorker
from voxkeep.modules.capture.worker import CaptureWorker
from voxkeep.modules.storage.public import StorageEvent
from voxkeep.shared.config import CaptureConfig
from voxkeep.shared.events import CaptureCommand, CaptureEvent, ProcessedFrame


def build_capture_module(
    *,
    event_queue: queue.Queue[CaptureEvent],
    command_queue: queue.Queue[CaptureCommand],
    storage_queue: queue.Queue[StorageEvent],
    stop_event: threading.Event,
    cfg: CaptureConfig,
) -> CaptureWorker:
    """Build the capture FSM worker."""
    return CaptureWorker(
        event_queue=event_queue,
        command_queue=command_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=cfg,
    )


def build_capture_detection_workers(
    *,
    wake_in_queue: queue.Queue[ProcessedFrame],
    vad_in_queue: queue.Queue[ProcessedFrame],
    event_queue: queue.Queue[CaptureEvent],
    stop_event: threading.Event,
    cfg: CaptureConfig,
) -> tuple[OpenWakeWordWorker, SileroVadWorker]:
    """Build independent wake and VAD consumers over audio fanout queues."""
    wake_worker = OpenWakeWordWorker(
        in_queue=wake_in_queue,
        out_queue=event_queue,
        stop_event=stop_event,
        rules=cfg.enabled_wake_rules,
    )
    vad_worker = SileroVadWorker(
        in_queue=vad_in_queue,
        out_queue=event_queue,
        stop_event=stop_event,
        speech_threshold=cfg.vad_speech_threshold,
        silence_ms=cfg.vad_silence_ms,
    )
    return wake_worker, vad_worker


__all__ = ["build_capture_detection_workers", "build_capture_module"]
