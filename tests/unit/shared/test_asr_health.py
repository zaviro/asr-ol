from __future__ import annotations

import threading

from websockets.sync.server import serve

from voxkeep.shared.asr_health import AsrHealthStatus
from voxkeep.shared.asr_health import classify_backend_health
from voxkeep.shared.asr_health import probe_websocket_handshake


def test_classify_backend_health_marks_tcp_only_probe_as_starting() -> None:
    status = classify_backend_health(
        tcp_ok=True,
        handshake_ok=None,
        detail="tcp reachable only",
    )

    assert status == AsrHealthStatus(
        state="starting",
        reason="tcp_only_probe",
        detail="tcp reachable only",
    )


def test_probe_websocket_handshake_succeeds_against_local_server() -> None:
    def handler(_ws) -> None:
        return None

    with serve(handler, "127.0.0.1", 0) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.socket.getsockname()[1]
            tcp_ok, handshake_ok, detail = probe_websocket_handshake(f"ws://127.0.0.1:{port}/")
        finally:
            server.shutdown()
            thread.join(timeout=1)

    assert tcp_ok is True
    assert handshake_ok is True
    assert "handshake ok" in detail


def test_probe_websocket_handshake_fails_for_closed_port() -> None:
    tcp_ok, handshake_ok, detail = probe_websocket_handshake("ws://127.0.0.1:9/")

    assert tcp_ok is False
    assert handshake_ok is False
    assert detail


def test_classify_backend_health_tcp_unreachable_returns_unavailable() -> None:
    status = classify_backend_health(
        tcp_ok=False,
        handshake_ok=None,
        detail="connection refused",
    )

    assert status.state == "unavailable"
    assert status.reason == "tcp_unreachable"


def test_classify_backend_health_handshake_ok_returns_healthy() -> None:
    status = classify_backend_health(
        tcp_ok=True,
        handshake_ok=True,
        detail="all good",
    )

    assert status.state == "healthy"
    assert status.reason == "ok"
