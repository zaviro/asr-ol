from __future__ import annotations

import queue
import threading

from voxkeep.modules.capture.domain.capture_fsm import CaptureWindow
from voxkeep.modules.capture.worker import CaptureWorker
from voxkeep.modules.storage.public import StorageEvent
from voxkeep.shared.config import CaptureConfig, WakeRuleConfig
from voxkeep.shared.events import AsrFinalEvent, CaptureCommand, CaptureEvent, VadEvent, WakeEvent


class FakeFSM:
    def on_wake(self, event: WakeEvent) -> None:
        _ = event

    def on_vad(self, event: VadEvent) -> CaptureWindow | None:
        if event.event_type == "speech_end":
            return CaptureWindow(
                session_id=1,
                keyword="hey_jarvis",
                start_ts=1.0,
                end_ts=1.5,
            )
        return None

    def tick(self) -> None:
        return


class FakeExtractor:
    def on_asr_final(self, event: AsrFinalEvent) -> None:
        _ = event

    def extract(self, start_ts: float, end_ts: float) -> str:
        _ = (start_ts, end_ts)
        return "route me"


def _capture_config() -> CaptureConfig:
    return CaptureConfig(
        wake_rules=(
            WakeRuleConfig(
                keyword="hey_jarvis", enabled=True, threshold=0.5, action="openclaw_agent"
            ),
            WakeRuleConfig(keyword="alexa", enabled=True, threshold=0.5, action="inject_text"),
        ),
        vad_speech_threshold=0.5,
        vad_silence_ms=300,
        pre_roll_ms=120,
        armed_timeout_ms=2000,
    )


def _worker(
    *,
    command_queue: queue.Queue[CaptureCommand],
    storage_queue: queue.Queue[StorageEvent],
) -> CaptureWorker:
    return CaptureWorker(
        event_queue=queue.Queue[CaptureEvent](),
        command_queue=command_queue,
        storage_queue=storage_queue,
        stop_event=threading.Event(),
        cfg=_capture_config(),
        _fsm=FakeFSM(),
        _transcript_extractor=FakeExtractor(),
    )


def test_capture_worker_routes_action_by_keyword() -> None:
    command_queue: queue.Queue[CaptureCommand] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    worker = _worker(command_queue=command_queue, storage_queue=storage_queue)

    worker._handle(VadEvent(ts=1.5, event_type="speech_end", score=0.1))

    command = command_queue.get_nowait()
    assert command.keyword == "hey_jarvis"
    assert command.action == "openclaw_agent"
    assert command.text == "route me"


def test_storage_receives_capture_only_after_command_enqueue_succeeds() -> None:
    command_queue: queue.Queue[CaptureCommand] = queue.Queue(maxsize=1)
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    occupied = CaptureCommand(
        session_id=99,
        keyword="occupied",
        action="inject_text",
        text="already queued",
        start_ts=0.0,
        end_ts=0.1,
    )
    command_queue.put_nowait(occupied)
    worker = _worker(command_queue=command_queue, storage_queue=storage_queue)

    worker._handle(VadEvent(ts=1.5, event_type="speech_end", score=0.1))

    assert command_queue.get_nowait() == occupied
    assert storage_queue.empty()

    worker._handle(VadEvent(ts=1.5, event_type="speech_end", score=0.1))

    command = command_queue.get_nowait()
    assert storage_queue.get_nowait() == command
