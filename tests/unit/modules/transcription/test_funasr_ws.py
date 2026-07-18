from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import threading
from typing import Any

import numpy as np
import pytest

from voxkeep.modules.transcription.infrastructure.funasr_ws import FunAsrWsEngine
from voxkeep.shared.config import AppConfig
from voxkeep.shared.events import ProcessedFrame


class _FakeReceiver:
    def __init__(self, messages: list[Any]) -> None:
        self._messages = iter(messages)

    def __aiter__(self) -> _FakeReceiver:
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._messages)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeSender:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def send(self, payload: Any) -> None:
        self.sent.append(payload)


def _frame(frame_id: int = 1) -> ProcessedFrame:
    return ProcessedFrame(
        frame_id=frame_id,
        data_int16=b"\x00\x00" * 512,
        pcm_f32=np.zeros(512, dtype=np.float32),
        sample_rate=16000,
        ts_start=1.0,
        ts_end=1.032,
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"binary", None),
        ("not-json", None),
        ("[]", None),
        ('{"mode":"2pass-offline","text":"ok"}', {"mode": "2pass-offline", "text": "ok"}),
    ],
)
def test_parse_message(raw: Any, expected: dict[str, Any] | None) -> None:
    assert FunAsrWsEngine._parse_message(raw) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"mode": "2pass-online", "is_final": True}, False),
        ({"mode": "online", "is_final": True}, False),
        ({"mode": "2pass-offline"}, True),
        ({"mode": "offline"}, True),
        ({"is_final": True}, True),
        ({"sentence_end": True}, True),
    ],
)
def test_is_final_distinguishes_two_pass_partial_and_corrected_results(
    payload: dict[str, Any], expected: bool
) -> None:
    assert FunAsrWsEngine._is_final(payload) is expected


def test_session_config_matches_official_funasr_two_pass_protocol(app_config: AppConfig) -> None:
    engine = FunAsrWsEngine(cfg=app_config.asr, stop_event=threading.Event())

    assert engine._session_config() == {
        "mode": "2pass",
        "chunk_size": [5, 10, 5],
        "chunk_interval": 10,
        "encoder_chunk_look_back": 4,
        "decoder_chunk_look_back": 1,
        "audio_fs": 16000,
        "wav_name": "microphone",
        "wav_format": "pcm",
        "is_speaking": True,
        "itn": True,
    }


def test_sender_wraps_binary_pcm_with_start_and_end_control_messages(
    app_config: AppConfig,
) -> None:
    stop = threading.Event()
    engine = FunAsrWsEngine(cfg=app_config.asr, stop_event=stop)
    ws = _FakeSender()
    engine.submit_frame(_frame())
    stop.set()

    asyncio.run(engine._sender(ws))

    assert json.loads(ws.sent[0])["is_speaking"] is True
    assert ws.sent[1] == _frame().data_int16
    assert json.loads(ws.sent[2]) == {"is_speaking": False}


def test_sender_reframes_audio_to_official_sixty_millisecond_chunks(
    app_config: AppConfig,
) -> None:
    stop = threading.Event()
    engine = FunAsrWsEngine(cfg=app_config.asr, stop_event=stop)
    ws = _FakeSender()
    engine.submit_frame(_frame(1))
    engine.submit_frame(_frame(2))
    stop.set()

    asyncio.run(engine._sender(ws))

    audio_messages = [message for message in ws.sent if isinstance(message, bytes)]
    assert [len(message) for message in audio_messages] == [1920, 128]


def test_receiver_emits_only_corrected_final_text(app_config: AppConfig) -> None:
    engine = FunAsrWsEngine(cfg=app_config.asr, stop_event=threading.Event())
    ws = _FakeReceiver(
        [
            '{"mode":"2pass-online","text":"partial","is_final":true}',
            '{"mode":"2pass-offline","text":" 最终文本 ","segment_id":"seg-1"}',
        ]
    )

    asyncio.run(engine._receiver(ws))

    event = engine.final_queue.get_nowait()
    assert event.text == "最终文本"
    assert event.segment_id == "seg-1"
    assert engine.final_queue.empty()


def test_submit_frame_drops_new_frame_when_queue_is_full(app_config: AppConfig) -> None:
    engine = FunAsrWsEngine(
        cfg=replace(app_config.asr, max_queue_size=1),
        stop_event=threading.Event(),
    )

    engine.submit_frame(_frame(1))
    engine.submit_frame(_frame(2))

    queued = engine._get_frame(timeout=0.0)
    assert queued is not None
    assert queued.frame_id == 1
    assert engine._get_frame(timeout=0.0) is None


def test_run_reconnects_after_session_failure(app_config: AppConfig, monkeypatch) -> None:
    stop = threading.Event()
    engine = FunAsrWsEngine(
        cfg=replace(app_config.asr, reconnect_initial_s=0.001, reconnect_max_s=0.004),
        stop_event=stop,
    )
    attempts = 0

    async def _run_session() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("boom")
        stop.set()

    monkeypatch.setattr(engine, "_run_session", _run_session)

    asyncio.run(engine._run())

    assert attempts == 2
