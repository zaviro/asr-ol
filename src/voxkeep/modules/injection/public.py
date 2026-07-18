"""Public construction API for the injection module."""

from __future__ import annotations

import queue
import threading

from voxkeep.modules.injection.infrastructure.factory import build_injector
from voxkeep.modules.injection.infrastructure.injector_worker import InjectorWorker
from voxkeep.shared.config import InjectorConfig
from voxkeep.shared.events import CaptureCommand


def build_injection_module(
    *,
    in_queue: queue.Queue[CaptureCommand],
    stop_event: threading.Event,
    cfg: InjectorConfig,
) -> InjectorWorker:
    """Build the action worker and its session-aware injector backend."""
    return InjectorWorker(
        in_queue=in_queue,
        stop_event=stop_event,
        injector=build_injector(cfg),
        openclaw_command=cfg.openclaw_command,
        openclaw_timeout_s=cfg.openclaw_timeout_s,
    )


__all__ = ["build_injection_module"]
