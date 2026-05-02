# Eliminate Legacy Worker Wrapper Layer

## Context

The architecture analysis identified that `WorkerCaptureModule` and `WorkerTranscriptionModule` wrap `CaptureWorker`/`AsrWorker` with unnecessary intermediate queues and bridge/fanout threads. The workers are already physically in the correct `modules/*/infrastructure/` directories, but the `public.py` files alias them as "Legacy" and add a redundant threading layer. This refactoring merges each worker into its module class, eliminating the double-class pattern.

## Changes

### 1. Capture module: merge `CaptureWorker` into `WorkerCaptureModule`

**Modify `src/voxkeep/modules/capture/public.py`:**
- Remove `LegacyCaptureWorker` import from `capture_worker`
- Move `_run`, `_consume_once`, `_emit_capture` logic from `CaptureWorker` into `WorkerCaptureModule`
- Remove `_public_out_queue` — emit `CaptureCommand` directly to `self._downstream_queue`
- Remove `_fanout_loop` thread — handler dispatch happens inline in `_emit_capture`
- Module's `start()` now launches its own event-loop thread instead of delegating to `CaptureWorker`

**Delete `src/voxkeep/modules/capture/infrastructure/capture_worker.py`**

### 2. Transcription module: merge `AsrWorker` into `WorkerTranscriptionModule`

**Modify `src/voxkeep/modules/transcription/public.py`:**
- Remove `LegacyAsrWorker` import from `asr_worker`
- Move `_run`, `_submit_audio_once`, `_drain_final_events`, `_fanout_event`, `_put_maybe_drop` into `WorkerTranscriptionModule`
- Remove `_final_in_queue` — drain directly from `self._backend_final_queue` (engine's queue)
- Remove `_backend_bridge_loop` thread — filtering of final-only events is already done in `_drain_final_events`
- Remove `_fanout_loop` thread — handler dispatch happens inline
- Move `_normalize_backend_event` to reside in this file (was in asr_worker.py)

**Delete `src/voxkeep/modules/transcription/infrastructure/asr_worker.py`**

### 3. Update tests

- **`tests/unit/modules/capture/test_capture_worker_routing.py`** — import `WorkerCaptureModule` from `public.py` instead of `CaptureWorker` from `capture_worker.py`
- **`tests/unit/modules/transcription/test_asr_worker.py`** — import `WorkerTranscriptionModule` from `public.py` instead of `AsrWorker` from `asr_worker.py`; update `_normalize_backend_event` import path
- **`tests/unit/modules/transcription/test_transcription_public_api.py`** — remove `_FakeWorker` class and two bridge-specific tests (mock paths referencing deleted `LegacyAsrWorker`)
- **`tests/e2e/test_pipeline_tts_audio.py`** — use `WorkerCaptureModule`/`WorkerTranscriptionModule` directly; adapt internal method calls
- **`tests/integration/test_openclaw_real_call.py`** — use `WorkerCaptureModule` with inline `CaptureConfig`

### 4. Side cleanup

- Remove empty legacy test directories: `tests/unit/{core,services,agents,tools,infra}`

### 5. No changes needed

- `bootstrap/runtime_app.py` — already uses `build_capture_module`/`build_transcription_module` factories; the returned modules already satisfy the `Worker` protocol (`start`/`join`/`is_alive`)
- `shared/` — no dependency on deleted files
- `__all__` exports remain backward-compatible

## Verification

1. `make lint` — ruff passes
2. `make test-unit` — all unit tests pass
3. `make test-architecture` — module boundary tests pass
4. `make test` — full test suite (151 passed, 2 skipped)
