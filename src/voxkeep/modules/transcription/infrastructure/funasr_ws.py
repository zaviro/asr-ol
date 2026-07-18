"""FunASR two-pass WebSocket transcription adapter."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import time
import uuid
from typing import Any, cast

from voxkeep.modules.transcription.application.backend_events import BackendTranscriptEvent
from voxkeep.modules.transcription.contracts import TranscriptionBackendEvent
from voxkeep.shared.config import AsrConfig
from voxkeep.shared.events import ProcessedFrame
from voxkeep.shared.interfaces import ASREngine
from voxkeep.shared.queue_utils import put_nowait_or_drop

logger = logging.getLogger(__name__)

_FRAME_POLL_TIMEOUT_S = 0.1


class FunAsrWsEngine(ASREngine):
    """Stream microphone PCM to a FunASR WebSocket service."""

    def __init__(self, cfg: AsrConfig, stop_event: threading.Event):
        """Initialize bounded queues and lifecycle state."""
        self._cfg = cfg
        self._stop_event = stop_event
        self._in_queue: queue.Queue[ProcessedFrame] = queue.Queue(maxsize=cfg.max_queue_size)
        self._final_queue: queue.Queue[BackendTranscriptEvent] = queue.Queue(
            maxsize=cfg.max_queue_size
        )
        self._thread: threading.Thread | None = None

    @property
    def final_queue(self) -> queue.Queue[TranscriptionBackendEvent]:
        """Return the queue receiving finalized transcript events."""
        return cast(queue.Queue[TranscriptionBackendEvent], self._final_queue)

    def start(self) -> None:
        """Start the background WebSocket worker once."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_thread, name="funasr_ws", daemon=True)
        self._thread.start()

    def submit_frame(self, frame: ProcessedFrame) -> None:
        """Queue one preprocessed PCM frame for FunASR."""
        put_nowait_or_drop(
            self._in_queue,
            frame,
            logger=logger,
            warning=f"funasr input queue full; dropping frame_id={frame.frame_id}",
        )

    def close(self) -> None:
        """Log a close request; shutdown is driven by the shared stop event."""
        logger.info("funasr websocket close requested")

    def join(self, timeout: float | None = None) -> None:
        """Join the background worker thread."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def _run_thread(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        backoff = self._cfg.reconnect_initial_s
        while not self._stop_event.is_set():
            try:
                await self._run_session()
                backoff = self._cfg.reconnect_initial_s
            except Exception as exc:
                logger.warning(
                    "funasr websocket session error endpoint=%s error=%s reconnect_in=%.1fs",
                    self._cfg.ws_url,
                    exc,
                    backoff,
                )
                should_stop = await asyncio.to_thread(self._stop_event.wait, backoff)
                if should_stop:
                    break
                backoff = min(self._cfg.reconnect_max_s, backoff * 2)
        logger.info("funasr websocket engine stopped")

    async def _run_session(self) -> None:
        try:
            import websockets
            from websockets.typing import Subprotocol
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("websockets package is required") from exc

        logger.info("funasr websocket connecting endpoint=%s", self._cfg.ws_url)
        async with websockets.connect(
            self._cfg.ws_url,
            ping_interval=None,
            max_size=2**22,
            subprotocols=[Subprotocol("binary")],
        ) as ws:
            logger.info("funasr websocket connected endpoint=%s", self._cfg.ws_url)
            sender = asyncio.create_task(self._sender(ws))
            receiver = asyncio.create_task(self._receiver(ws))
            stopper = asyncio.create_task(asyncio.to_thread(self._stop_event.wait))

            done, pending = await asyncio.wait(
                {sender, receiver, stopper},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc is not None:
                    raise exc

    async def _sender(self, ws: Any) -> None:
        await ws.send(json.dumps(self._session_config()))
        pending_pcm = bytearray()
        target_bytes = self._stream_chunk_bytes()
        while not self._stop_event.is_set() or not self._in_queue.empty():
            frame = await asyncio.to_thread(self._get_frame, _FRAME_POLL_TIMEOUT_S)
            if frame is None:
                continue
            pending_pcm.extend(frame.data_int16)
            while len(pending_pcm) >= target_bytes:
                await ws.send(bytes(pending_pcm[:target_bytes]))
                del pending_pcm[:target_bytes]
        if pending_pcm:
            await ws.send(bytes(pending_pcm))
        await ws.send(json.dumps({"is_speaking": False}))

    async def _receiver(self, ws: Any) -> None:
        async for raw in ws:
            if self._stop_event.is_set():
                return
            payload = self._parse_message(raw)
            if payload is None or not self._is_final(payload):
                continue

            text = str(payload.get("text") or payload.get("result") or "").strip()
            if not text:
                continue

            now = time.time()
            event = BackendTranscriptEvent(
                segment_id=str(payload.get("segment_id") or payload.get("sid") or uuid.uuid4()),
                text=text,
                start_ts=float(payload.get("start") or payload.get("start_time") or now),
                end_ts=float(payload.get("end") or payload.get("end_time") or now),
                event_type="final",
            )
            put_nowait_or_drop(
                self._final_queue,
                event,
                logger=logger,
                warning=f"funasr final queue full; dropping segment_id={event.segment_id}",
            )

    def _session_config(self) -> dict[str, Any]:
        return {
            "mode": self._cfg.funasr_mode,
            "chunk_size": list(self._cfg.funasr_chunk_size),
            "chunk_interval": self._cfg.funasr_chunk_interval,
            "encoder_chunk_look_back": self._cfg.funasr_encoder_chunk_look_back,
            "decoder_chunk_look_back": self._cfg.funasr_decoder_chunk_look_back,
            "audio_fs": self._cfg.sample_rate,
            "wav_name": "microphone",
            "wav_format": "pcm",
            "is_speaking": True,
            "itn": self._cfg.funasr_itn,
        }

    def _stream_chunk_bytes(self) -> int:
        chunk_ms = 60 * self._cfg.funasr_chunk_size[1] / self._cfg.funasr_chunk_interval
        samples = int(self._cfg.sample_rate * chunk_ms / 1000)
        return samples * 2

    def _get_frame(self, timeout: float) -> ProcessedFrame | None:
        try:
            return self._in_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @staticmethod
    def _parse_message(raw: Any) -> dict[str, Any] | None:
        if isinstance(raw, bytes) or not isinstance(raw, str):
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _is_final(payload: dict[str, Any]) -> bool:
        mode = str(payload.get("mode") or "").lower()
        if mode in {"online", "2pass-online"}:
            return False
        if mode in {"offline", "2pass-offline", "final"}:
            return True
        return bool(
            payload.get("is_final") is True
            or payload.get("sentence_end") is True
            or payload.get("type") == "final"
        )


__all__ = ["FunAsrWsEngine"]
