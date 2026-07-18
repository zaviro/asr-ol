"""Public construction API for the storage module."""

from __future__ import annotations

import queue
import threading

from voxkeep.modules.storage.contracts import StorageEvent
from voxkeep.modules.storage.infrastructure.sqlite_storage_worker import SqliteStorageWorker
from voxkeep.shared.config import StorageConfig


def build_storage_module(
    *,
    in_queue: queue.Queue[StorageEvent],
    stop_event: threading.Event,
    cfg: StorageConfig,
) -> SqliteStorageWorker:
    """Build the single SQLite-backed storage worker."""
    return SqliteStorageWorker(
        in_queue=in_queue,
        stop_event=stop_event,
        sqlite_path=cfg.sqlite_path,
        jsonl_debug_path=cfg.jsonl_debug_path,
    )


__all__ = ["StorageEvent", "build_storage_module"]
