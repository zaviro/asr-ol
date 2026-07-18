from __future__ import annotations

import os
import shutil

import pytest

from voxkeep.shared.config import (
    AppConfig,
    AsrConfig,
    AudioEngineConfig,
    CaptureConfig,
    InjectorConfig,
    StorageConfig,
    WakeRuleConfig,
)


@pytest.fixture
def app_config() -> AppConfig:
    audio_engine = AudioEngineConfig(
        sample_rate=16000,
        channels=1,
        frame_ms=20,
        max_queue_size=16,
    )
    asr = AsrConfig(
        backend="funasr_ws",
        external_host="127.0.0.1",
        external_port=10096,
        external_path="/",
        use_ssl=False,
        reconnect_initial_s=1.0,
        reconnect_max_s=30.0,
        funasr_mode="2pass",
        funasr_chunk_size=(5, 10, 5),
        funasr_chunk_interval=10,
        funasr_encoder_chunk_look_back=4,
        funasr_decoder_chunk_look_back=1,
        funasr_itn=True,
        max_queue_size=16,
        sample_rate=16000,
    )
    capture = CaptureConfig(
        wake_threshold=0.5,
        wake_rules=(
            WakeRuleConfig(
                keyword="alexa",
                enabled=True,
                threshold=0.5,
                action="inject_text",
            ),
            WakeRuleConfig(
                keyword="hey_jarvis",
                enabled=True,
                threshold=0.6,
                action="openclaw_agent",
            ),
        ),
        vad_speech_threshold=0.5,
        vad_silence_ms=800,
        pre_roll_ms=600,
        armed_timeout_ms=5000,
        max_queue_size=16,
    )
    storage = StorageConfig(
        sqlite_path=":memory:",
        store_final_only=True,
        jsonl_debug_path=None,
        max_queue_size=16,
    )
    injector = InjectorConfig(
        backend="auto",
        auto_enter=False,
        xdotool_delay_ms=1,
        openclaw_command=("openclaw", "agent", "--message", "{text}"),
        openclaw_timeout_s=20.0,
        max_queue_size=16,
    )
    return AppConfig(
        audio_engine=audio_engine,
        asr=asr,
        capture=capture,
        storage=storage,
        injector=injector,
        log_level="INFO",
    )


@pytest.fixture
def require_openclaw_real() -> None:
    if os.environ.get("VOXKEEP_RUN_OPENCLAW_REAL") != "1":
        pytest.skip("set VOXKEEP_RUN_OPENCLAW_REAL=1 to run real OpenClaw integration tests")
    if shutil.which("openclaw") is None:
        pytest.skip("openclaw command not found in PATH")
