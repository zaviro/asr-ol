from __future__ import annotations

import queue
import threading

import numpy as np
import pytest

from voxkeep.modules.storage.public import StorageEvent
from voxkeep.modules.transcription import public as transcription_public
from voxkeep.modules.transcription import worker as transcription_worker
from voxkeep.modules.transcription.contracts import TranscriptionEngine
from voxkeep.shared.config import AsrConfig
from voxkeep.shared.events import AsrFinalEvent, CaptureEvent, ProcessedFrame


class FakeEngine:
    def __init__(self) -> None:
        self.final_queue: queue.Queue[AsrFinalEvent] = queue.Queue()
        self.started = 0
        self.closed = 0
        self.joined = 0
        self.submitted: list[ProcessedFrame] = []

    def start(self) -> None:
        self.started += 1

    def submit_frame(self, frame: ProcessedFrame) -> None:
        self.submitted.append(frame)

    def close(self) -> None:
        self.closed += 1

    def join(self, timeout: float | None = None) -> None:
        _ = timeout
        self.joined += 1


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


def _frame() -> ProcessedFrame:
    return ProcessedFrame(
        frame_id=1,
        data_int16=b"\x00\x00" * 160,
        pcm_f32=np.zeros(160, dtype=np.float32),
        sample_rate=16000,
        ts_start=1.0,
        ts_end=1.01,
    )


def test_builder_wires_injected_queues_config_and_stop_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_engine = FakeEngine()
    config = _config()
    stop_event = threading.Event()
    audio_queue: queue.Queue[ProcessedFrame] = queue.Queue()
    capture_queue: queue.Queue[CaptureEvent] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    received: dict[str, object] = {}

    def build_engine(*, cfg: AsrConfig) -> FakeEngine:
        received.update(cfg=cfg)
        return fake_engine

    monkeypatch.setattr(transcription_worker, "FunAsrWsEngine", build_engine)

    worker = transcription_public.build_transcription_module(
        audio_queue=audio_queue,
        capture_queue=capture_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=config,
    )

    assert isinstance(worker, transcription_worker.TranscriptionWorker)
    assert received == {"cfg": config}


def test_built_worker_runs_engine_and_publishes_direct_final_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_engine = FakeEngine()
    monkeypatch.setattr(
        transcription_worker,
        "FunAsrWsEngine",
        lambda *, cfg: fake_engine,
    )
    stop_event = threading.Event()
    audio_queue: queue.Queue[ProcessedFrame] = queue.Queue()
    capture_queue: queue.Queue[CaptureEvent] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    frame = _frame()
    event = AsrFinalEvent(
        segment_id="seg-1",
        text="hello",
        start_ts=1.0,
        end_ts=1.2,
    )
    audio_queue.put(frame)
    fake_engine.final_queue.put(event)
    stop_event.set()
    worker = transcription_public.build_transcription_module(
        audio_queue=audio_queue,
        capture_queue=capture_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=_config(),
    )

    worker.start()
    worker.join(timeout=2)

    assert fake_engine.started == 1
    assert fake_engine.closed == 1
    assert fake_engine.joined == 1
    assert fake_engine.submitted == [frame]
    assert capture_queue.get_nowait() is event
    assert storage_queue.get_nowait() is event


def test_transcription_engine_contract_includes_lifecycle_and_audio_methods() -> None:
    assert {"start", "submit_frame", "close", "join", "final_queue"} <= set(
        TranscriptionEngine.__dict__
    )
