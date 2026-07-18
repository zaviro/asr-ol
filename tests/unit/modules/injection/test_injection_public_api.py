from __future__ import annotations

import queue
import threading

from voxkeep.modules.injection.public import build_injection_module
from voxkeep.shared.config import AppConfig


def test_build_injection_module_wires_configured_worker(monkeypatch, app_config: AppConfig) -> None:
    built: dict[str, object] = {}
    injector = object()
    worker = object()

    monkeypatch.setattr("voxkeep.modules.injection.public.build_injector", lambda _cfg: injector)

    def fake_worker(**kwargs):  # type: ignore[no-untyped-def]
        built.update(kwargs)
        return worker

    monkeypatch.setattr("voxkeep.modules.injection.public.InjectorWorker", fake_worker)
    in_queue = queue.Queue()
    stop_event = threading.Event()

    result = build_injection_module(
        in_queue=in_queue,
        stop_event=stop_event,
        cfg=app_config.injector,
    )

    assert result is worker
    assert built["in_queue"] is in_queue
    assert built["stop_event"] is stop_event
    assert built["injector"] is injector
    assert built["openclaw_command"] == app_config.injector.openclaw_command
