"""Normalized ASR backend health helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AsrHealthStatus:
    """Canonical backend health classification."""

    state: str
    reason: str
    detail: str


def probe_websocket_handshake(url: str) -> tuple[bool, bool, str]:
    """Attempt a real WebSocket handshake against ``url``.

    Returns:
        A tuple of ``(tcp_ok, handshake_ok, detail)``.
    """
    try:
        from websockets.sync.client import connect
    except Exception as exc:  # pragma: no cover - dependency failure is environmental
        return False, False, f"websockets import failed: {type(exc).__name__}: {exc}"

    try:
        with connect(url, open_timeout=1.5, proxy=None):
            pass
    except OSError as exc:
        return False, False, f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        return True, False, f"{type(exc).__name__}: {exc}"
    return True, True, f"websocket handshake ok: {url}"


def classify_backend_health(
    *,
    tcp_ok: bool,
    handshake_ok: bool | None,
    detail: str,
) -> AsrHealthStatus:
    """Classify a backend probe into a normalized health status."""
    if not tcp_ok:
        return AsrHealthStatus(
            state="unavailable",
            reason="tcp_unreachable",
            detail=detail,
        )
    if handshake_ok is None:
        return AsrHealthStatus(
            state="starting",
            reason="tcp_only_probe",
            detail=detail,
        )
    if not handshake_ok:
        return AsrHealthStatus(
            state="degraded",
            reason="handshake_failed",
            detail=detail,
        )
    return AsrHealthStatus(
        state="healthy",
        reason="ok",
        detail=detail,
    )


__all__ = [
    "AsrHealthStatus",
    "classify_backend_health",
    "probe_websocket_handshake",
]
