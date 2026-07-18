"""Build and supervise the complete local audio-to-action pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import queue
import threading
import time
from typing import Protocol

from voxkeep.modules.audio_engine.public import AudioEngine, build_audio_engine
from voxkeep.modules.capture.public import build_capture_detection_workers, build_capture_module
from voxkeep.modules.injection.public import build_injection_module
from voxkeep.modules.storage.public import StorageEvent, build_storage_module
from voxkeep.modules.transcription.public import build_transcription_module
from voxkeep.shared.config import AppConfig
from voxkeep.shared.events import CaptureCommand, CaptureEvent, ProcessedFrame

logger = logging.getLogger(__name__)

_RUN_FOREVER_POLL_S = 0.2


class _Worker(Protocol):
    """Lifecycle shape shared by runtime workers."""

    def start(self) -> None: ...

    def join(self, timeout: float | None = None) -> None: ...

    def is_alive(self) -> bool: ...


@dataclass(slots=True)
class PipelineQueues:
    """All bounded queues that connect runtime modules."""

    wake_audio: queue.Queue[ProcessedFrame]
    vad_audio: queue.Queue[ProcessedFrame]
    asr_audio: queue.Queue[ProcessedFrame]
    capture_events: queue.Queue[CaptureEvent]
    capture_commands: queue.Queue[CaptureCommand]
    storage_events: queue.Queue[StorageEvent]

    @classmethod
    def create(cls, maxsize: int) -> PipelineQueues:
        """Create every pipeline queue with one shared capacity."""
        return cls(
            wake_audio=queue.Queue(maxsize=maxsize),
            vad_audio=queue.Queue(maxsize=maxsize),
            asr_audio=queue.Queue(maxsize=maxsize),
            capture_events=queue.Queue(maxsize=maxsize),
            capture_commands=queue.Queue(maxsize=maxsize),
            storage_events=queue.Queue(maxsize=maxsize),
        )

    @property
    def sizes(self) -> dict[str, int]:
        """Return externally meaningful queue depths."""
        return {
            "wake_audio_queue": self.wake_audio.qsize(),
            "vad_audio_queue": self.vad_audio.qsize(),
            "asr_audio_queue": self.asr_audio.qsize(),
            "capture_event_queue": self.capture_events.qsize(),
            "capture_command_queue": self.capture_commands.qsize(),
            "storage_queue": self.storage_events.qsize(),
        }


@dataclass(slots=True, frozen=True)
class WorkerSpec:
    """Name one supervised worker and its shutdown timeout."""

    name: str
    worker: _Worker
    join_timeout_s: float = 2.0


@dataclass(slots=True)
class RuntimeSignals:
    """Independent stop signals for each producer-to-consumer stage."""

    requested: threading.Event
    audio: threading.Event
    analysis: threading.Event
    capture: threading.Event
    outputs: threading.Event

    @classmethod
    def create(cls) -> RuntimeSignals:
        """Create an unset signal for every shutdown stage."""
        return cls(
            requested=threading.Event(),
            audio=threading.Event(),
            analysis=threading.Event(),
            capture=threading.Event(),
            outputs=threading.Event(),
        )


@dataclass(slots=True, frozen=True)
class ShutdownStage:
    """Signal and workers that can stop after their producers finish."""

    signal: threading.Event
    workers: tuple[WorkerSpec, ...]


@dataclass(slots=True, frozen=True)
class RuntimeComponents:
    """Concrete modules assembled for one runtime instance."""

    audio: AudioEngine
    storage: _Worker
    capture: _Worker
    injection: _Worker
    wake: _Worker
    vad: _Worker
    transcription: _Worker

    @property
    def startup(self) -> tuple[WorkerSpec, ...]:
        """Return consumer-first startup order."""
        return (
            WorkerSpec("storage", self.storage),
            WorkerSpec("capture", self.capture),
            WorkerSpec("injection", self.injection),
            WorkerSpec("wake", self.wake),
            WorkerSpec("vad", self.vad),
            WorkerSpec("transcription", self.transcription, 3.0),
            WorkerSpec("audio", self.audio),
        )

    def downstream_shutdown(self, signals: RuntimeSignals) -> tuple[ShutdownStage, ...]:
        """Return producer-first stages for lossless downstream draining."""
        return (
            ShutdownStage(
                signals.analysis,
                (
                    WorkerSpec("wake", self.wake),
                    WorkerSpec("vad", self.vad),
                    WorkerSpec("transcription", self.transcription, 3.0),
                ),
            ),
            ShutdownStage(signals.capture, (WorkerSpec("capture", self.capture),)),
            ShutdownStage(
                signals.outputs,
                (
                    WorkerSpec("injection", self.injection),
                    WorkerSpec("storage", self.storage),
                ),
            ),
        )


class AppRuntime:
    """Supervise already-assembled runtime components."""

    def __init__(
        self,
        *,
        signals: RuntimeSignals,
        queues: PipelineQueues,
        components: RuntimeComponents,
    ) -> None:
        """Create a supervisor around an assembled runtime."""
        self._signals = signals
        self.queues = queues
        self.components = components
        self._fatal_error: str | None = None
        self._stop_lock = threading.Lock()
        self._stopped = False

    @property
    def stop_event(self) -> threading.Event:
        """Expose the operator-facing shutdown request signal."""
        return self._signals.requested

    @property
    def fatal_error(self) -> str | None:
        """Return the fatal worker-health error, if one occurred."""
        return self._fatal_error

    @property
    def queue_sizes(self) -> dict[str, int]:
        """Return queue depths without exposing queue objects."""
        return {**self.components.audio.queue_sizes, **self.queues.sizes}

    def start(self) -> None:
        """Start all consumers before live audio production."""
        logger.info("runtime starting")
        try:
            for spec in self.components.startup:
                spec.worker.start()
        except Exception:
            self.stop_event.set()
            logger.exception("runtime startup failed")
            self.stop()
            raise
        logger.info("runtime started")

    def run_forever(self) -> None:
        """Monitor workers until shutdown or a fatal exit."""
        while not self.stop_event.is_set():
            unhealthy = [
                spec.name for spec in self.components.startup if not spec.worker.is_alive()
            ]
            if unhealthy:
                self._fatal_error = f"worker stopped unexpectedly: {', '.join(unhealthy)}"
                logger.error(self._fatal_error)
                self.stop_event.set()
                return
            time.sleep(_RUN_FOREVER_POLL_S)

    def stop(self) -> None:
        """Stop each producer stage, then drain its downstream consumers."""
        with self._stop_lock:
            if self._stopped:
                return
            self._stopped = True

        logger.info("runtime stopping")
        self.stop_event.set()

        # Stop live production first. The audio bus drains raw input while all
        # analysis consumers are still running.
        self.components.audio.stop()
        self.components.audio.join(timeout=2.0)
        self._warn_if_alive(WorkerSpec("audio", self.components.audio))

        # Each later stage remains alive until every producer feeding it has
        # joined, preventing a temporarily empty queue from causing early exit.
        for stage in self.components.downstream_shutdown(self._signals):
            stage.signal.set()
            for spec in stage.workers:
                spec.worker.join(timeout=spec.join_timeout_s)
                self._warn_if_alive(spec)
        logger.info("runtime stopped")

    @staticmethod
    def _warn_if_alive(spec: WorkerSpec) -> None:
        if spec.worker.is_alive():
            logger.warning(
                "worker did not stop within %.1fs name=%s",
                spec.join_timeout_s,
                spec.name,
            )


def build_runtime(cfg: AppConfig) -> AppRuntime:
    """Create queues, module workers, and their lifecycle supervisor."""
    signals = RuntimeSignals.create()
    queues = PipelineQueues.create(cfg.audio_engine.max_queue_size)

    audio = build_audio_engine(
        cfg=cfg.audio_engine,
        stop_event=signals.audio,
        wake_queue=queues.wake_audio,
        vad_queue=queues.vad_audio,
        asr_queue=queues.asr_audio,
    )
    wake, vad = build_capture_detection_workers(
        wake_in_queue=queues.wake_audio,
        vad_in_queue=queues.vad_audio,
        event_queue=queues.capture_events,
        stop_event=signals.analysis,
        cfg=cfg.capture,
    )
    transcription = build_transcription_module(
        audio_queue=queues.asr_audio,
        capture_queue=queues.capture_events,
        storage_queue=queues.storage_events,
        stop_event=signals.analysis,
        cfg=cfg.asr,
    )
    capture = build_capture_module(
        event_queue=queues.capture_events,
        command_queue=queues.capture_commands,
        storage_queue=queues.storage_events,
        stop_event=signals.capture,
        cfg=cfg.capture,
    )
    injection = build_injection_module(
        in_queue=queues.capture_commands,
        stop_event=signals.outputs,
        cfg=cfg.injector,
    )
    storage = build_storage_module(
        in_queue=queues.storage_events,
        stop_event=signals.outputs,
        cfg=cfg.storage,
    )
    components = RuntimeComponents(
        audio=audio,
        storage=storage,
        capture=capture,
        injection=injection,
        wake=wake,
        vad=vad,
        transcription=transcription,
    )
    return AppRuntime(signals=signals, queues=queues, components=components)


__all__ = ["AppRuntime", "build_runtime"]
