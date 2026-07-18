from datetime import datetime
import json
from pathlib import Path
import queue
import sqlite3
import threading
import time

import pytest

from voxkeep.modules.storage.contracts import StorageEvent
from voxkeep.shared.events import AsrFinalEvent, CaptureCommand
from voxkeep.modules.storage.infrastructure.sqlite_storage_worker import (
    SqliteStorageWorker as StorageWorker,
)


def _asr(
    text: str,
    start_ts: float,
    end_ts: float,
) -> AsrFinalEvent:
    return AsrFinalEvent(
        segment_id=text,
        text=text,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def _capture(text: str, start_ts: float, end_ts: float) -> CaptureCommand:
    return CaptureCommand(
        session_id=1,
        keyword="alexa",
        action="inject_text",
        text=text,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def _count_rows(db_path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("select count(*) from asr_segments").fetchone()[0]
    finally:
        conn.close()


def _stored_rows(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            """
            select source, text, start_ts, end_ts, is_final, created_at, meta_json
            from asr_segments
            order by id
            """
        ).fetchall()
    finally:
        conn.close()


def _assert_utc_timestamp(value: str) -> None:
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None


def test_storage_worker_normalizes_events_to_sqlite_and_jsonl_on_stop_flush(tmp_path):
    q: queue.Queue[StorageEvent] = queue.Queue()
    stop = threading.Event()
    db_path = tmp_path / "asr.db"
    jsonl_path = tmp_path / "debug" / "asr.jsonl"

    worker = StorageWorker(
        q,
        stop,
        sqlite_path=str(db_path),
        jsonl_debug_path=str(jsonl_path),
        commit_batch_size=100,
        commit_flush_interval_s=60.0,
    )
    worker.start()

    q.put(_asr("hello", 1.0, 1.2))
    q.put(_capture("world", 2.0, 2.2))

    stop.set()
    worker.join(timeout=2)

    rows = _stored_rows(db_path)
    assert len(rows) == 2
    assert tuple(rows[0][field] for field in ("source", "text", "is_final")) == (
        "stream",
        "hello",
        1,
    )
    assert rows[0]["start_ts"] == pytest.approx(1.0)
    assert rows[0]["end_ts"] == pytest.approx(1.2)
    assert rows[0]["meta_json"] is None
    _assert_utc_timestamp(rows[0]["created_at"])

    assert tuple(rows[1][field] for field in ("source", "text", "is_final")) == (
        "capture",
        "world",
        1,
    )
    assert rows[1]["start_ts"] == pytest.approx(2.0)
    assert rows[1]["end_ts"] == pytest.approx(2.2)
    assert rows[1]["meta_json"] is None
    _assert_utc_timestamp(rows[1]["created_at"])

    jsonl_records = [json.loads(line) for line in jsonl_path.read_text().splitlines()]
    assert [
        {
            "source": record["source"],
            "text": record["text"],
            "start_ts": record["start_ts"],
            "end_ts": record["end_ts"],
            "is_final": record["is_final"],
            "meta_json": record["meta_json"],
        }
        for record in jsonl_records
    ] == [
        {
            "source": "stream",
            "text": "hello",
            "start_ts": 1.0,
            "end_ts": 1.2,
            "is_final": True,
            "meta_json": None,
        },
        {
            "source": "capture",
            "text": "world",
            "start_ts": 2.0,
            "end_ts": 2.2,
            "is_final": True,
            "meta_json": None,
        },
    ]
    for row, record in zip(rows, jsonl_records, strict=True):
        assert record["created_at"] == row["created_at"]
        _assert_utc_timestamp(record["created_at"])


def test_storage_worker_flushes_on_batch_size_without_stop(tmp_path):
    q: queue.Queue[StorageEvent] = queue.Queue()
    stop = threading.Event()
    db_path = tmp_path / "asr.db"

    worker = StorageWorker(
        q,
        stop,
        sqlite_path=str(db_path),
        commit_batch_size=2,
        commit_flush_interval_s=60.0,
    )
    worker.start()

    q.put(_asr("a", 1.0, 1.1))
    q.put(_asr("b", 1.1, 1.2))

    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            if _count_rows(db_path) == 2:
                break
        except sqlite3.OperationalError:
            pass
        time.sleep(0.02)

    stop.set()
    worker.join(timeout=2)

    assert _count_rows(db_path) == 2
