from __future__ import annotations

import pytest

from voxkeep.shared.asr_backends import BUILTIN_BACKENDS
from voxkeep.shared.asr_backends import resolve_backend_definition


def test_builtin_registry_contains_qwen_vllm() -> None:
    assert "qwen_vllm" in BUILTIN_BACKENDS
    backend = resolve_backend_definition("qwen_vllm")

    assert backend.kind == "external_service"
    assert backend.transport == "websocket"


def test_resolve_backend_definition_normalizes_input() -> None:
    backend = resolve_backend_definition("QWEN_VLLM")

    assert backend.backend_id == "qwen_vllm"


def test_resolve_backend_definition_strips_whitespace() -> None:
    backend = resolve_backend_definition("  qwen_vllm  ")

    assert backend.backend_id == "qwen_vllm"


def test_resolve_backend_definition_raises_for_unknown_backend() -> None:
    with pytest.raises(ValueError, match="unsupported asr backend"):
        resolve_backend_definition("unknown_backend")


def test_resolve_backend_definition_raises_for_empty_string() -> None:
    with pytest.raises(ValueError, match="unsupported asr backend"):
        resolve_backend_definition("")


def test_builtin_backend_has_correct_attributes() -> None:
    backend = resolve_backend_definition("qwen_vllm")

    assert backend.display_name == "Qwen3-ASR vLLM External"
    assert backend.managed_by_default is False
