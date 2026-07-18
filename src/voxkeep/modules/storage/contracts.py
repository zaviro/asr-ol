"""Internal storage records and accepted persistence events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from voxkeep.shared.events import AsrFinalEvent, CaptureCommand


StorageEvent: TypeAlias = AsrFinalEvent | CaptureCommand


@dataclass(slots=True, frozen=True)
class StorageRecord:
    """Normalized row written by the storage worker."""

    source: str
    text: str
    start_ts: float
    end_ts: float
    created_at: str
    meta_json: str | None = None
