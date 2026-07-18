from __future__ import annotations

import queue
import threading
import time

from voxkeep.modules.capture.public import build_capture_module
from voxkeep.modules.storage.public import StorageEvent
from voxkeep.shared.config import AppConfig
from voxkeep.shared.events import (
    AsrFinalEvent,
    CaptureCommand,
    CaptureEvent,
    VadEvent,
    WakeEvent,
)


def test_capture_module_forwards_command_and_storage_event(app_config: AppConfig) -> None:
    event_queue: queue.Queue[CaptureEvent] = queue.Queue()
    command_queue: queue.Queue[CaptureCommand] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    stop_event = threading.Event()
    worker = build_capture_module(
        event_queue=event_queue,
        command_queue=command_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=app_config.capture,
    )
    worker.start()

    try:
        base = time.time()
        event_queue.put(WakeEvent(ts=base, score=0.9, keyword="alexa"))
        event_queue.put(
            AsrFinalEvent(
                segment_id="seg-1",
                text="hello world",
                start_ts=base,
                end_ts=base + 0.3,
            )
        )
        event_queue.put(VadEvent(ts=base + 0.1, event_type="speech_start", score=0.8))
        event_queue.put(VadEvent(ts=base + 0.4, event_type="speech_end", score=0.1))

        command = command_queue.get(timeout=2.0)
        stored = storage_queue.get(timeout=2.0)
    finally:
        stop_event.set()
        worker.join(timeout=2.0)

    assert command.action == "inject_text"
    assert command.text == "hello world"
    assert stored == command


def test_capture_worker_waits_for_late_matching_asr_final_within_grace(
    app_config: AppConfig,
) -> None:
    event_queue: queue.Queue[CaptureEvent] = queue.Queue()
    command_queue: queue.Queue[CaptureCommand] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    stop_event = threading.Event()
    worker = build_capture_module(
        event_queue=event_queue,
        command_queue=command_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=app_config.capture,
    )
    worker.start()

    try:
        base = time.time()
        event_queue.put(WakeEvent(ts=base, score=0.9, keyword="alexa"))
        event_queue.put(VadEvent(ts=base + 0.1, event_type="speech_start", score=0.8))
        event_queue.put(VadEvent(ts=base + 0.4, event_type="speech_end", score=0.1))
        # This final is deliberately ordered after speech_end. The worker must
        # hold the completed window during its final-transcript grace period.
        event_queue.put(
            AsrFinalEvent(
                segment_id="late-seg",
                text="late but matching",
                start_ts=base + 0.15,
                end_ts=base + 0.35,
            )
        )

        command = command_queue.get(timeout=0.75)
    finally:
        stop_event.set()
        worker.join(timeout=2.0)

    assert command.text == "late but matching"
    assert storage_queue.get_nowait() == command


def test_capture_worker_recovers_vad_start_delivered_before_wake(
    app_config: AppConfig,
) -> None:
    event_queue: queue.Queue[CaptureEvent] = queue.Queue()
    command_queue: queue.Queue[CaptureCommand] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    stop_event = threading.Event()
    worker = build_capture_module(
        event_queue=event_queue,
        command_queue=command_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=app_config.capture,
    )
    worker.start()

    try:
        base = time.time()
        # The wake producer is slower, so arrival order differs from event time.
        event_queue.put(VadEvent(ts=base + 0.1, event_type="speech_start", score=0.8))
        event_queue.put(WakeEvent(ts=base, score=0.9, keyword="alexa"))
        event_queue.put(
            AsrFinalEvent(
                segment_id="out-of-order",
                text="still captured",
                start_ts=base + 0.1,
                end_ts=base + 0.3,
            )
        )
        event_queue.put(VadEvent(ts=base + 0.4, event_type="speech_end", score=0.1))

        command = command_queue.get(timeout=0.75)
    finally:
        stop_event.set()
        worker.join(timeout=2.0)

    assert command.text == "still captured"
    assert storage_queue.get_nowait() == command


def test_capture_worker_arms_inside_an_active_vad_utterance(app_config: AppConfig) -> None:
    event_queue: queue.Queue[CaptureEvent] = queue.Queue()
    command_queue: queue.Queue[CaptureCommand] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    stop_event = threading.Event()
    worker = build_capture_module(
        event_queue=event_queue,
        command_queue=command_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=app_config.capture,
    )
    worker.start()

    try:
        base = time.time()
        event_queue.put(VadEvent(ts=base, event_type="speech_start", score=0.8))
        event_queue.put(WakeEvent(ts=base + 0.1, score=0.9, keyword="alexa"))
        event_queue.put(
            AsrFinalEvent(
                segment_id="continuous-utterance",
                text="wake and command",
                start_ts=base + 0.1,
                end_ts=base + 0.3,
            )
        )
        event_queue.put(VadEvent(ts=base + 0.4, event_type="speech_end", score=0.1))

        command = command_queue.get(timeout=0.75)
    finally:
        stop_event.set()
        worker.join(timeout=2.0)

    assert command.text == "wake and command"
    assert storage_queue.get_nowait() == command
