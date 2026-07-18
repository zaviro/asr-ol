from __future__ import annotations

import queue
import threading

from voxkeep.modules.audio_engine.public import AudioEngine, build_audio_engine
from voxkeep.shared.config import AppConfig
from voxkeep.shared.events import RawAudioChunk


class FakeSource:
    def __init__(self, calls: list[object], *, start_error: Exception | None = None) -> None:
        self._calls = calls
        self._start_error = start_error

    def start(self) -> None:
        self._calls.append("source.start")
        if self._start_error is not None:
            raise self._start_error

    def stop(self) -> None:
        self._calls.append("source.stop")


class FakeBus:
    def __init__(self, calls: list[object], *, alive: bool = True) -> None:
        self._calls = calls
        self._alive = alive

    def start(self) -> None:
        self._calls.append("bus.start")

    def join(self, timeout: float | None = None) -> None:
        self._calls.append(("bus.join", timeout))

    def is_alive(self) -> bool:
        return self._alive


def test_audio_engine_owns_source_and_bus_lifecycle() -> None:
    calls: list[object] = []
    stop_event = threading.Event()
    engine = AudioEngine(
        source=FakeSource(calls),
        bus=FakeBus(calls),
        stop_event=stop_event,
        raw_queue=queue.Queue(),
    )

    engine.start()
    assert engine.is_alive()

    engine.stop()
    engine.join(timeout=2.0)

    assert calls == ["bus.start", "source.start", "source.stop", ("bus.join", 2.0)]
    assert stop_event.is_set()


def test_audio_engine_stops_bus_when_microphone_start_fails() -> None:
    calls: list[object] = []
    stop_event = threading.Event()
    engine = AudioEngine(
        source=FakeSource(calls, start_error=RuntimeError("microphone unavailable")),
        bus=FakeBus(calls),
        stop_event=stop_event,
        raw_queue=queue.Queue(),
    )

    try:
        engine.start()
    except RuntimeError as exc:
        assert str(exc) == "microphone unavailable"
    else:  # pragma: no cover - assertion aid
        raise AssertionError("expected microphone start failure")

    assert calls == ["bus.start", "source.start", "source.stop", ("bus.join", 1.0)]
    assert stop_event.is_set()


def test_builder_uses_injected_raw_queue(app_config: AppConfig) -> None:
    stop_event = threading.Event()
    raw_queue: queue.Queue[RawAudioChunk] = queue.Queue(maxsize=1)
    engine = build_audio_engine(
        cfg=app_config.audio_engine,
        stop_event=stop_event,
        raw_queue=raw_queue,
        wake_queue=queue.Queue(),
        vad_queue=queue.Queue(),
        asr_queue=queue.Queue(),
    )

    raw_queue.put(
        RawAudioChunk(
            data=b"",
            frames=0,
            sample_rate=app_config.audio_engine.sample_rate,
            channels=app_config.audio_engine.channels,
            ts=0.0,
        )
    )

    assert engine.queue_sizes == {"raw_queue": 1}
