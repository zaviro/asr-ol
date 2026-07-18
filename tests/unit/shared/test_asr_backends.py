from __future__ import annotations

import pytest

from voxkeep.shared.asr_backends import BUILTIN_BACKENDS
from voxkeep.shared.asr_backends import resolve_backend_definition


def test_builtin_registry_contains_funasr_ws() -> None:
    assert "funasr_ws" in BUILTIN_BACKENDS
    backend = resolve_backend_definition("funasr_ws")

    assert backend.kind == "managed_service"
    assert backend.transport == "websocket"


def test_resolve_backend_definition_normalizes_input() -> None:
    backend = resolve_backend_definition("FUNASR_WS")

    assert backend.backend_id == "funasr_ws"


def test_resolve_backend_definition_strips_whitespace() -> None:
    backend = resolve_backend_definition("  funasr_ws  ")

    assert backend.backend_id == "funasr_ws"


def test_resolve_backend_definition_raises_for_unknown_backend() -> None:
    with pytest.raises(ValueError, match="unsupported asr backend"):
        resolve_backend_definition("unknown_backend")


def test_resolve_backend_definition_raises_for_empty_string() -> None:
    with pytest.raises(ValueError, match="unsupported asr backend"):
        resolve_backend_definition("")


def test_builtin_backend_has_correct_attributes() -> None:
    backend = resolve_backend_definition("funasr_ws")

    assert backend.display_name == "FunASR 2-pass WebSocket"
    assert backend.managed_by_default is True
