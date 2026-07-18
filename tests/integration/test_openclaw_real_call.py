from __future__ import annotations

import json
import queue
import subprocess
import threading
import time

from voxkeep.modules.capture.public import build_capture_module
from voxkeep.modules.storage.public import StorageEvent
from voxkeep.shared.config import CaptureConfig, WakeRuleConfig
from voxkeep.shared.events import (
    AsrFinalEvent,
    CaptureCommand,
    CaptureEvent,
    VadEvent,
    WakeEvent,
)


def test_openclaw_triggered_by_wake_with_asr_hi_returns_payload(require_openclaw_real: None):
    prompt_text = "请忽略其他内容，只回复：你好这里是openclaw"
    agents = subprocess.run(
        ["openclaw", "agents", "list", "--json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(agents.stdout)
    assert any(item.get("id") == "main" for item in payload if isinstance(item, dict))

    event_queue: queue.Queue[CaptureEvent] = queue.Queue()
    command_queue: queue.Queue[CaptureCommand] = queue.Queue()
    storage_queue: queue.Queue[StorageEvent] = queue.Queue()
    stop_event = threading.Event()

    cfg = CaptureConfig(
        wake_rules=(
            WakeRuleConfig(
                keyword="hey_jarvis", enabled=True, threshold=0.5, action="openclaw_agent"
            ),
        ),
        vad_speech_threshold=0.5,
        vad_silence_ms=300,
        pre_roll_ms=200,
        armed_timeout_ms=2000,
    )

    worker = build_capture_module(
        event_queue=event_queue,
        command_queue=command_queue,
        storage_queue=storage_queue,
        stop_event=stop_event,
        cfg=cfg,
    )
    worker.start()

    base = time.time()
    event_queue.put(WakeEvent(ts=base, score=0.9, keyword="hey_jarvis"))
    event_queue.put(
        AsrFinalEvent(
            segment_id="seg-1",
            text=prompt_text,
            start_ts=base + 0.05,
            end_ts=base + 0.3,
        )
    )
    event_queue.put(VadEvent(ts=base + 0.1, event_type="speech_start", score=0.9))
    event_queue.put(VadEvent(ts=base + 0.5, event_type="speech_end", score=0.1))
    try:
        cmd = command_queue.get(timeout=2.0)
    finally:
        stop_event.set()
        worker.join(timeout=2.0)

    assert cmd.action == "openclaw_agent"
    assert cmd.keyword == "hey_jarvis"
    assert cmd.text == prompt_text
    assert storage_queue.get_nowait() == cmd

    proc = subprocess.run(
        [
            "openclaw",
            "agent",
            "--agent",
            "main",
            "--message",
            cmd.text,
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    result = json.loads(proc.stdout)
    assert result["status"] == "ok"
    texts = [
        item.get("text", "")
        for item in result.get("result", {}).get("payloads", [])
        if isinstance(item, dict)
    ]
    assert any("你好这里是openclaw" in text for text in texts)
