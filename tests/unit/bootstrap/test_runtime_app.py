from __future__ import annotations

import threading

import pytest

import voxkeep.bootstrap.runtime_app as runtime_app_module
from voxkeep.bootstrap.runtime_app import (
    AppRuntime,
    PipelineQueues,
    RuntimeComponents,
    RuntimeSignals,
    WorkerSpec,
    build_runtime,
)
from voxkeep.shared.config import AppConfig


class FakeWorker:
    """Small structural fake for the lifecycle contract."""

    def __init__(
        self,
        name: str,
        calls: list[str],
        *,
        start_error: Exception | None = None,
    ) -> None:
        self.name = name
        self.calls = calls
        self.start_error = start_error
        self.alive = False

    def start(self) -> None:
        self.calls.append(f"start:{self.name}")
        if self.start_error is not None:
            raise self.start_error
        self.alive = True

    def join(self, timeout: float | None = None) -> None:
        self.calls.append(f"join:{self.name}:{timeout}")
        self.alive = False

    def is_alive(self) -> bool:
        return self.alive


class FakeAudio(FakeWorker):
    def __init__(
        self,
        calls: list[str],
        stop_event: threading.Event,
        *,
        start_error: Exception | None = None,
        raw_queue_size: int = 0,
    ) -> None:
        super().__init__("audio", calls, start_error=start_error)
        self.stop_event = stop_event
        self.queue_sizes = {"raw_queue": raw_queue_size}
        self.stopped_after_signal = False

    def start(self) -> None:
        try:
            super().start()
        except Exception:
            # The real AudioEngine signals all workers when microphone startup fails.
            self.stop_event.set()
            raise

    def stop(self) -> None:
        self.stop_event.set()
        self.stopped_after_signal = self.stop_event.is_set()
        self.calls.append("stop:audio")


def _runtime_fixture(
    *,
    audio_start_error: Exception | None = None,
    raw_queue_size: int = 0,
) -> tuple[AppRuntime, dict[str, FakeWorker], list[str]]:
    calls: list[str] = []
    signals = RuntimeSignals.create()
    workers: dict[str, FakeWorker] = {
        name: FakeWorker(name, calls)
        for name in ("storage", "capture", "injection", "wake", "vad", "transcription")
    }
    audio = FakeAudio(
        calls,
        signals.audio,
        start_error=audio_start_error,
        raw_queue_size=raw_queue_size,
    )
    workers["audio"] = audio
    components = RuntimeComponents(
        audio=audio,  # type: ignore[arg-type]
        storage=workers["storage"],
        capture=workers["capture"],
        injection=workers["injection"],
        wake=workers["wake"],
        vad=workers["vad"],
        transcription=workers["transcription"],
    )
    runtime = AppRuntime(
        signals=signals,
        queues=PipelineQueues.create(maxsize=4),
        components=components,
    )
    return runtime, workers, calls


def test_pipeline_queues_are_distinct_and_bounded() -> None:
    queues = PipelineQueues.create(maxsize=7)
    all_queues = (
        queues.wake_audio,
        queues.vad_audio,
        queues.asr_audio,
        queues.capture_events,
        queues.capture_commands,
        queues.storage_events,
    )

    assert len({id(item) for item in all_queues}) == len(all_queues)
    assert {item.maxsize for item in all_queues} == {7}
    assert queues.sizes == {
        "wake_audio_queue": 0,
        "vad_audio_queue": 0,
        "asr_audio_queue": 0,
        "capture_event_queue": 0,
        "capture_command_queue": 0,
        "storage_queue": 0,
    }


def test_runtime_components_define_readable_lifecycle_plans() -> None:
    runtime, _, _ = _runtime_fixture()

    startup = runtime.components.startup
    stages = runtime.components.downstream_shutdown(runtime._signals)
    shutdown = [spec for stage in stages for spec in stage.workers]

    assert all(isinstance(spec, WorkerSpec) for spec in (*startup, *shutdown))
    assert [spec.name for spec in startup] == [
        "storage",
        "capture",
        "injection",
        "wake",
        "vad",
        "transcription",
        "audio",
    ]
    assert [spec.name for spec in shutdown] == [
        "wake",
        "vad",
        "transcription",
        "capture",
        "injection",
        "storage",
    ]
    assert next(spec.join_timeout_s for spec in shutdown if spec.name == "transcription") == 3.0
    assert [stage.signal for stage in stages] == [
        runtime._signals.analysis,
        runtime._signals.capture,
        runtime._signals.outputs,
    ]


def test_runtime_starts_and_stops_components_once_in_dependency_order() -> None:
    runtime, workers, calls = _runtime_fixture()

    runtime.start()
    runtime.stop()
    runtime.stop()

    assert runtime.stop_event.is_set()
    assert all(
        signal.is_set()
        for signal in (
            runtime._signals.audio,
            runtime._signals.analysis,
            runtime._signals.capture,
            runtime._signals.outputs,
        )
    )
    assert isinstance(workers["audio"], FakeAudio)
    assert workers["audio"].stopped_after_signal
    assert calls == [
        "start:storage",
        "start:capture",
        "start:injection",
        "start:wake",
        "start:vad",
        "start:transcription",
        "start:audio",
        "stop:audio",
        "join:audio:2.0",
        "join:wake:2.0",
        "join:vad:2.0",
        "join:transcription:3.0",
        "join:capture:2.0",
        "join:injection:2.0",
        "join:storage:2.0",
    ]


def test_runtime_propagates_audio_start_failure_and_signals_shutdown() -> None:
    runtime, _, calls = _runtime_fixture(audio_start_error=RuntimeError("microphone unavailable"))

    with pytest.raises(RuntimeError, match="microphone unavailable"):
        runtime.start()

    assert runtime.stop_event.is_set()
    assert calls == [
        "start:storage",
        "start:capture",
        "start:injection",
        "start:wake",
        "start:vad",
        "start:transcription",
        "start:audio",
        "stop:audio",
        "join:audio:2.0",
        "join:wake:2.0",
        "join:vad:2.0",
        "join:transcription:3.0",
        "join:capture:2.0",
        "join:injection:2.0",
        "join:storage:2.0",
    ]


def test_run_forever_reports_every_dead_worker() -> None:
    runtime, workers, _ = _runtime_fixture()
    runtime.start()
    workers["wake"].alive = False
    workers["transcription"].alive = False

    runtime.run_forever()

    assert runtime.stop_event.is_set()
    assert runtime.fatal_error == "worker stopped unexpectedly: wake, transcription"


def test_run_forever_exits_cleanly_after_external_shutdown() -> None:
    runtime, _, _ = _runtime_fixture()
    runtime.stop_event.set()

    runtime.run_forever()

    assert runtime.fatal_error is None


def test_runtime_queue_sizes_combine_audio_and_pipeline_queues() -> None:
    runtime, _, _ = _runtime_fixture(raw_queue_size=3)
    runtime.queues.wake_audio.put(object())  # type: ignore[arg-type]
    runtime.queues.capture_commands.put(object())  # type: ignore[arg-type]

    assert runtime.queue_sizes == {
        "raw_queue": 3,
        "wake_audio_queue": 1,
        "vad_audio_queue": 0,
        "asr_audio_queue": 0,
        "capture_event_queue": 0,
        "capture_command_queue": 1,
        "storage_queue": 0,
    }


def test_build_runtime_connects_each_consumer_to_the_audio_fanout(
    monkeypatch: pytest.MonkeyPatch,
    app_config: AppConfig,
) -> None:
    calls: list[str] = []
    built: dict[str, dict[str, object]] = {}
    workers = {
        name: FakeWorker(name, calls)
        for name in ("storage", "capture", "injection", "wake", "vad", "transcription")
    }
    audio: FakeAudio | None = None

    def build_audio(**kwargs: object) -> FakeAudio:
        nonlocal audio
        built["audio"] = kwargs
        audio = FakeAudio(calls, kwargs["stop_event"])  # type: ignore[arg-type]
        return audio

    def build_detectors(**kwargs: object) -> tuple[FakeWorker, FakeWorker]:
        built["detectors"] = kwargs
        return workers["wake"], workers["vad"]

    def worker_builder(name: str):  # type: ignore[no-untyped-def]
        def build(**kwargs: object) -> FakeWorker:
            built[name] = kwargs
            return workers[name]

        return build

    monkeypatch.setattr(runtime_app_module, "build_audio_engine", build_audio)
    monkeypatch.setattr(runtime_app_module, "build_capture_detection_workers", build_detectors)
    monkeypatch.setattr(runtime_app_module, "build_capture_module", worker_builder("capture"))
    monkeypatch.setattr(runtime_app_module, "build_injection_module", worker_builder("injection"))
    monkeypatch.setattr(runtime_app_module, "build_storage_module", worker_builder("storage"))
    monkeypatch.setattr(
        runtime_app_module,
        "build_transcription_module",
        worker_builder("transcription"),
    )

    runtime = build_runtime(app_config)

    wake_audio = built["audio"]["wake_queue"]
    vad_audio = built["audio"]["vad_queue"]
    assert wake_audio is runtime.queues.wake_audio
    assert vad_audio is runtime.queues.vad_audio
    assert wake_audio is not vad_audio
    assert built["detectors"]["wake_in_queue"] is wake_audio
    assert built["detectors"]["vad_in_queue"] is vad_audio
    assert built["audio"]["asr_queue"] is built["transcription"]["audio_queue"]

    capture_events = runtime.queues.capture_events
    assert built["detectors"]["event_queue"] is capture_events
    assert built["transcription"]["capture_queue"] is capture_events
    assert built["capture"]["event_queue"] is capture_events
    assert built["capture"]["command_queue"] is built["injection"]["in_queue"]
    assert built["capture"]["storage_queue"] is built["storage"]["in_queue"]
    assert built["transcription"]["storage_queue"] is built["storage"]["in_queue"]

    assert built["audio"]["stop_event"] is not runtime.stop_event
    assert built["detectors"]["stop_event"] is built["transcription"]["stop_event"]
    assert built["capture"]["stop_event"] is not built["transcription"]["stop_event"]
    assert built["injection"]["stop_event"] is built["storage"]["stop_event"]

    assert runtime.components.audio is audio
    assert runtime.components.wake is workers["wake"]
    assert runtime.components.vad is workers["vad"]
