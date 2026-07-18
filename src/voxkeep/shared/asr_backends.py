"""Built-in ASR backend registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AsrBackendDefinition:
    """Describe one built-in ASR backend."""

    backend_id: str
    display_name: str
    kind: str
    transport: str
    managed_by_default: bool = False


BUILTIN_BACKENDS: dict[str, AsrBackendDefinition] = {
    "funasr_ws": AsrBackendDefinition(
        backend_id="funasr_ws",
        display_name="FunASR 2-pass WebSocket",
        kind="managed_service",
        transport="websocket",
        managed_by_default=True,
    ),
}


def resolve_backend_definition(backend_id: str) -> AsrBackendDefinition:
    """Return the registered backend definition for ``backend_id``."""
    normalized = backend_id.strip().lower()
    try:
        return BUILTIN_BACKENDS[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported asr backend: {backend_id}") from exc


__all__ = ["AsrBackendDefinition", "BUILTIN_BACKENDS", "resolve_backend_definition"]
