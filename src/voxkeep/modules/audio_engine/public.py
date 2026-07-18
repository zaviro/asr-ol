"""Public construction and lifecycle API for desktop audio capture."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Protocol

from voxkeep.modules.audio_engine.infrastructure.audio_bus import AudioBus
from voxkeep.modules.audio_engine.infrastructure.audio_capture import SoundDeviceAudioSource
from voxkeep.shared.config import AudioEngineConfig
from voxkeep.shared.events import ProcessedFrame, RawAudioChunk

logger = logging.getLogger(__name__)


class _AudioSource(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


class _AudioBus(Protocol):
    def start(self) -> None: ...

    def join(self, timeout: float | None = None) -> None: ...

    def is_alive(self) -> bool: ...


class AudioEngine:
    """Own microphone capture and preprocessing fanout as one runtime component."""

    def __init__(
        self,
        *,
        source: _AudioSource,
        bus: _AudioBus,
        stop_event: threading.Event,
        raw_queue: queue.Queue[RawAudioChunk],
    ) -> None:
        """Create an audio engine from its synchronous source and background bus."""
        self._source = source
        self._bus = bus
        self._stop_event = stop_event
        self._raw_queue = raw_queue

    @property
    def queue_sizes(self) -> dict[str, int]:
        """Return queue sizes owned by the audio engine."""
        return {"raw_queue": self._raw_queue.qsize()}

    def start(self) -> None:
        """Start fanout before opening the microphone stream."""
        self._bus.start()
        try:
            self._source.start()
        except Exception:
            logger.exception("audio source start failed")
            try:
                self._source.stop()
            except Exception:
                logger.exception("audio source cleanup failed after start error")
            self._stop_event.set()
            self._bus.join(timeout=1.0)
            raise

    def stop(self) -> None:
        """Close the microphone, then allow the bus to drain queued audio."""
        try:
            self._source.stop()
        except Exception:
            logger.exception("audio source stop failed")
        finally:
            self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        """Wait for the audio bus to finish draining."""
        self._bus.join(timeout=timeout)

    def is_alive(self) -> bool:
        """Report whether the audio bus is running."""
        return self._bus.is_alive()


def build_audio_engine(
    *,
    cfg: AudioEngineConfig,
    stop_event: threading.Event,
    wake_queue: queue.Queue[ProcessedFrame],
    vad_queue: queue.Queue[ProcessedFrame],
    asr_queue: queue.Queue[ProcessedFrame],
    raw_queue: queue.Queue[RawAudioChunk] | None = None,
) -> AudioEngine:
    """Build the audio engine, optionally using a caller-owned raw audio queue."""
    capture_queue = raw_queue
    if capture_queue is None:
        capture_queue = queue.Queue(maxsize=cfg.max_queue_size)

    source = SoundDeviceAudioSource(out_queue=capture_queue, cfg=cfg)
    bus = AudioBus(
        raw_queue=capture_queue,
        wake_queue=wake_queue,
        vad_queue=vad_queue,
        asr_queue=asr_queue,
        stop_event=stop_event,
    )
    return AudioEngine(
        source=source,
        bus=bus,
        stop_event=stop_event,
        raw_queue=capture_queue,
    )


__all__ = ["AudioEngine", "build_audio_engine"]
