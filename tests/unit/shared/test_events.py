from __future__ import annotations

import numpy as np

from voxkeep.shared.events import (
    AsrFinalEvent,
    CaptureCommand,
    ProcessedFrame,
    RawAudioChunk,
    StorageRecord,
    VadEvent,
    WakeEvent,
)


def test_raw_audio_chunk_slots() -> None:
    chunk = RawAudioChunk(
        data=b"abc",
        frames=3,
        sample_rate=16000,
        channels=1,
        ts=1.5,
    )

    assert chunk.data == b"abc"
    assert chunk.frames == 3
    assert chunk.sample_rate == 16000
    assert chunk.channels == 1
    assert chunk.ts == 1.5


def test_processed_frame_slots() -> None:
    pcm = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    frame = ProcessedFrame(
        frame_id=42,
        data_int16=b"\x00\x01",
        pcm_f32=pcm,
        sample_rate=16000,
        ts_start=1.0,
        ts_end=1.5,
    )

    assert frame.frame_id == 42
    assert frame.ts_start == 1.0
    assert frame.ts_end == 1.5


def test_wake_event_slots() -> None:
    event = WakeEvent(ts=10.0, score=0.85, keyword="alexa")

    assert event.ts == 10.0
    assert event.score == 0.85
    assert event.keyword == "alexa"


def test_vad_event_speech_start() -> None:
    event = VadEvent(ts=5.0, event_type="speech_start", score=0.9)

    assert event.ts == 5.0
    assert event.event_type == "speech_start"
    assert event.score == 0.9


def test_vad_event_speech_end() -> None:
    event = VadEvent(ts=8.0, event_type="speech_end", score=0.3)

    assert event.ts == 8.0
    assert event.event_type == "speech_end"
    assert event.score == 0.3


def test_asr_final_event_defaults_to_final() -> None:
    event = AsrFinalEvent(
        segment_id="seg-1",
        text="hello world",
        start_ts=1.0,
        end_ts=2.0,
    )

    assert event.is_final is True


def test_asr_final_event_can_be_non_final() -> None:
    event = AsrFinalEvent(
        segment_id="seg-1",
        text="hello",
        start_ts=1.0,
        end_ts=1.5,
        is_final=False,
    )

    assert event.is_final is False


def test_capture_command_slots() -> None:
    cmd = CaptureCommand(
        session_id=1,
        keyword="alexa",
        action="inject_text",
        text="turn on the lights",
        start_ts=10.0,
        end_ts=12.0,
    )

    assert cmd.session_id == 1
    assert cmd.keyword == "alexa"
    assert cmd.action == "inject_text"
    assert cmd.text == "turn on the lights"


def test_storage_record_with_meta() -> None:
    record = StorageRecord(
        source="asr",
        text="test transcription",
        start_ts=1.0,
        end_ts=2.0,
        is_final=True,
        created_at="2024-01-01T00:00:00",
        meta_json='{"confidence": 0.95}',
    )

    assert record.source == "asr"
    assert record.meta_json == '{"confidence": 0.95}'


def test_storage_record_without_meta() -> None:
    record = StorageRecord(
        source="capture",
        text="short command",
        start_ts=1.0,
        end_ts=1.5,
        is_final=True,
        created_at="2024-01-01T00:00:00",
    )

    assert record.meta_json is None
