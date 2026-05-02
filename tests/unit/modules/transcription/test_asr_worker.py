from __future__ import annotations

import queue
import threading

import numpy as np
import pytest

from voxkeep.modules.transcription.application.backend_events import BackendTranscriptEvent
from voxkeep.modules.transcription.public import (
    WorkerTranscriptionModule,
    _normalize_backend_event,
)
from voxkeep.shared.config import AppConfig
from voxkeep.shared.events import AsrFinalEvent, ProcessedFrame


class FakeEngine:
    def __init__(self) -> None:
        self.final_queue: queue.Queue[BackendTranscriptEvent] = queue.Queue()
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


def _frame(frame_id: int = 1, ts_start: float = 1.0) -> ProcessedFrame:
    return ProcessedFrame(
        frame_id=frame_id,
        data_int16=(b"\x00\x00" * 160),
        pcm_f32=np.zeros(160, dtype=np.float32),
        sample_rate=16000,
        ts_start=ts_start,
        ts_end=ts_start + 0.01,
    )


def _backend_event(*, text: str = "hello", event_type: str = "final") -> BackendTranscriptEvent:
    return BackendTranscriptEvent(
        segment_id="seg-1",
        text=text,
        start_ts=1.0,
        end_ts=1.2,
        event_type=event_type,
    )


def _make_module(
    *,
    engine: FakeEngine,
    in_q: queue.Queue[ProcessedFrame] | None = None,
    capture_q: queue.Queue[AsrFinalEvent] | None = None,
    storage_q: queue.Queue | None = None,
    stop: threading.Event | None = None,
    store_final_only: bool = True,
    app_config: AppConfig,
) -> WorkerTranscriptionModule:
    from dataclasses import replace

    storage_cfg = replace(app_config.storage, store_final_only=store_final_only)
    return WorkerTranscriptionModule(
        capture_queue=capture_q or queue.Queue(),
        storage_queue=storage_q or queue.Queue(),
        stop_event=stop or threading.Event(),
        asr_cfg=app_config.asr,
        storage_cfg=storage_cfg,
        in_queue=in_q or queue.Queue(),
        _engine=engine,
    )


@pytest.mark.parametrize(
    ("store_final_only", "expected_storage"),
    [
        (True, 1),
        (False, 1),
    ],
)
def test_drain_final_events_fanout_and_storage_policy(
    store_final_only: bool,
    expected_storage: int,
    app_config: AppConfig,
) -> None:
    engine = FakeEngine()
    capture_q: queue.Queue[AsrFinalEvent] = queue.Queue()
    storage_q = queue.Queue()

    module = _make_module(
        engine=engine,
        capture_q=capture_q,
        storage_q=storage_q,
        store_final_only=store_final_only,
        app_config=app_config,
    )

    event = _backend_event(text="hello", event_type="final")
    engine.final_queue.put(event)

    module._drain_final_events()

    capture_event = capture_q.get_nowait()
    assert isinstance(capture_event, AsrFinalEvent)
    assert capture_event.text == event.text
    assert storage_q.qsize() == expected_storage


def test_drain_final_events_ignores_backend_partial_events(app_config: AppConfig) -> None:
    engine = FakeEngine()
    capture_q: queue.Queue[AsrFinalEvent] = queue.Queue()
    storage_q = queue.Queue()

    module = _make_module(
        engine=engine, capture_q=capture_q, storage_q=storage_q, app_config=app_config
    )

    engine.final_queue.put(_backend_event(event_type="partial"))

    module._drain_final_events()

    assert capture_q.empty()
    assert storage_q.empty()


def test_drain_final_events_ignores_backend_partial_events_when_store_final_only_is_false(
    app_config: AppConfig,
) -> None:
    engine = FakeEngine()
    capture_q: queue.Queue[AsrFinalEvent] = queue.Queue()
    storage_q = queue.Queue()

    module = _make_module(
        engine=engine,
        capture_q=capture_q,
        storage_q=storage_q,
        store_final_only=False,
        app_config=app_config,
    )

    engine.final_queue.put(_backend_event(event_type="partial"))

    module._drain_final_events()

    assert capture_q.empty()
    assert storage_q.empty()


def test_drain_final_events_normalizes_backend_final_events(app_config: AppConfig) -> None:
    engine = FakeEngine()
    capture_q: queue.Queue[AsrFinalEvent] = queue.Queue()
    storage_q = queue.Queue()

    module = _make_module(
        engine=engine, capture_q=capture_q, storage_q=storage_q, app_config=app_config
    )

    engine.final_queue.put(_backend_event(text="normalized"))

    module._drain_final_events()

    capture_event = capture_q.get_nowait()
    storage_event = storage_q.get_nowait()

    assert isinstance(capture_event, AsrFinalEvent)
    assert capture_event.text == "normalized"
    assert storage_event.text == "normalized"


def test_normalize_backend_event_accepts_structural_backend_event() -> None:
    from types import SimpleNamespace

    event = SimpleNamespace(
        segment_id="seg-1",
        text="structural",
        start_ts=1.0,
        end_ts=1.2,
        is_final=True,
    )

    normalized = _normalize_backend_event(event)

    assert isinstance(normalized, AsrFinalEvent)
    assert normalized.text == "structural"


def test_run_submits_audio_and_closes_engine(app_config: AppConfig):
    in_q: queue.Queue[ProcessedFrame] = queue.Queue()
    engine = FakeEngine()
    capture_q: queue.Queue[AsrFinalEvent] = queue.Queue()
    storage_q = queue.Queue()
    stop = threading.Event()

    module = _make_module(
        engine=engine,
        in_q=in_q,
        capture_q=capture_q,
        storage_q=storage_q,
        stop=stop,
        app_config=app_config,
    )

    in_q.put(_frame())
    engine.final_queue.put(_backend_event())
    stop.set()

    module._run()

    assert len(engine.submitted) == 1
    assert capture_q.qsize() == 1
    assert storage_q.qsize() == 1
    assert engine.closed == 1


def test_join_forwards_timeout_to_engine(app_config: AppConfig):
    engine = FakeEngine()

    module = _make_module(engine=engine, app_config=app_config)

    module.join(timeout=1.5)

    assert engine.join_timeouts == [1.5]


def test_start_is_idempotent_for_engine(app_config: AppConfig):
    engine = FakeEngine()
    stop = threading.Event()

    module = _make_module(engine=engine, stop=stop, app_config=app_config)

    module.start()
    module.start()
    stop.set()
    module.join(timeout=1)

    assert engine.started == 1
