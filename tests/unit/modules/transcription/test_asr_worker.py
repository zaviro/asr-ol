from __future__ import annotations

import logging
import queue
import threading

import numpy as np
import pytest

from voxkeep.modules.storage.public import StorageEvent
from voxkeep.modules.transcription.worker import TranscriptionWorker
from voxkeep.shared.config import AsrConfig
from voxkeep.shared.events import AsrFinalEvent, CaptureEvent, ProcessedFrame


class FakeEngine:
    def __init__(self) -> None:
        self.final_queue: queue.Queue[AsrFinalEvent] = queue.Queue()
        self.started = 0
        self.closed = 0
        self.submitted: list[ProcessedFrame] = []
        self.join_timeouts: list[float | None] = []

    def start(self) -> None:
        self.started += 1

    def submit_frame(self, frame: ProcessedFrame) -> None:
        self.submitted.append(frame)

    def close(self) -> None:
        self.closed += 1

    def join(self, timeout: float | None = None) -> None:
        self.join_timeouts.append(timeout)


def _config() -> AsrConfig:
    return AsrConfig(
        backend="funasr_ws",
        external_host="127.0.0.1",
        external_port=10096,
        external_path="/",
        use_ssl=False,
        reconnect_initial_s=1.0,
        reconnect_max_s=30.0,
        funasr_mode="2pass",
        funasr_chunk_size=(5, 10, 5),
        funasr_chunk_interval=10,
        funasr_encoder_chunk_look_back=4,
        funasr_decoder_chunk_look_back=1,
        funasr_itn=True,
        max_queue_size=16,
        sample_rate=16000,
    )


def _frame(frame_id: int = 1) -> ProcessedFrame:
    return ProcessedFrame(
        frame_id=frame_id,
        data_int16=b"\x00\x00" * 160,
        pcm_f32=np.zeros(160, dtype=np.float32),
        sample_rate=16000,
        ts_start=1.0,
        ts_end=1.01,
    )


def _event(*, text: str = "hello") -> AsrFinalEvent:
    return AsrFinalEvent(
        segment_id="seg-1",
        text=text,
        start_ts=1.0,
        end_ts=1.2,
    )


def _worker(
    engine: FakeEngine,
    *,
    audio_queue: queue.Queue[ProcessedFrame] | None = None,
    capture_queue: queue.Queue[CaptureEvent] | None = None,
    storage_queue: queue.Queue[StorageEvent] | None = None,
    stop_event: threading.Event | None = None,
) -> TranscriptionWorker:
    return TranscriptionWorker(
        audio_queue=audio_queue if audio_queue is not None else queue.Queue(),
        capture_queue=capture_queue if capture_queue is not None else queue.Queue(),
        storage_queue=storage_queue if storage_queue is not None else queue.Queue(),
        stop_event=stop_event if stop_event is not None else threading.Event(),
        cfg=_config(),
        _engine=engine,
    )


def test_run_submits_audio_fans_out_final_event_and_closes_engine() -> None:
    engine = FakeEngine()
    audio_queue: queue.Queue[ProcessedFrame] = queue.Queue()
    capture_queue: queue.Queue[CaptureEvent] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    stop_event = threading.Event()
    frame = _frame()
    event = _event()
    audio_queue.put(frame)
    engine.final_queue.put(event)
    stop_event.set()
    worker = _worker(
        engine,
        audio_queue=audio_queue,
        capture_queue=capture_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
    )

    worker._run()

    assert engine.submitted == [frame]
    assert capture_queue.get_nowait() is event
    assert storage_queue.get_nowait() is event
    assert engine.closed == 1


@pytest.mark.parametrize("full_target", ["capture", "storage"])
def test_full_output_queue_drops_event_without_blocking_other_target(
    full_target: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine = FakeEngine()
    capture_queue: queue.Queue[CaptureEvent] = queue.Queue(maxsize=1)
    storage_queue: queue.Queue[StorageEvent] = queue.Queue(maxsize=1)
    existing = _event(text="existing")
    if full_target == "capture":
        capture_queue.put(existing)
    else:
        storage_queue.put(existing)
    event = _event(text="new")
    engine.final_queue.put(event)
    worker = _worker(engine, capture_queue=capture_queue, storage_queue=storage_queue)

    with caplog.at_level(logging.WARNING):
        worker._drain_final_events()

    full_queue = capture_queue if full_target == "capture" else storage_queue
    other_queue = storage_queue if full_target == "capture" else capture_queue
    assert full_queue.get_nowait() is existing
    assert other_queue.get_nowait() is event
    assert f"{full_target} queue full; dropping final transcript" in caplog.text


def test_start_is_idempotent_and_join_forwards_timeout() -> None:
    engine = FakeEngine()
    stop_event = threading.Event()
    stop_event.set()
    worker = _worker(engine, stop_event=stop_event)

    worker.start()
    worker.start()
    worker.join(timeout=1.5)

    assert engine.started == 1
    assert engine.closed == 1
    assert engine.join_timeouts == [1.5]
    assert not worker.is_alive()


def test_join_before_start_is_safe() -> None:
    engine = FakeEngine()
    worker = _worker(engine)

    worker.join(timeout=0.25)

    assert engine.join_timeouts == [0.25]
    assert not worker.is_alive()


def test_join_fans_out_final_event_produced_during_engine_shutdown() -> None:
    event = _event(text="shutdown final")

    class LateFinalEngine(FakeEngine):
        def join(self, timeout: float | None = None) -> None:
            super().join(timeout)
            self.final_queue.put(event)

    engine = LateFinalEngine()
    capture_queue: queue.Queue[CaptureEvent] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    worker = _worker(
        engine,
        capture_queue=capture_queue,
        storage_queue=storage_queue,
    )

    worker.join(timeout=0.25)

    assert capture_queue.get_nowait() is event
    assert storage_queue.get_nowait() is event
