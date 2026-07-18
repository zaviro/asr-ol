# Architecture

VoxKeep is a modular monolith. It runs as one host process, uses threads and bounded queues for
the live audio pipeline, and keeps each business capability behind a module-level public API.

## Reading order

For a first pass through the code, read:

1. `src/voxkeep/cli/main.py` for operator-facing commands.
2. `src/voxkeep/bootstrap/runtime_app.py` for construction and lifecycle.
3. `src/voxkeep/shared/events.py` for messages exchanged by workers.
4. `src/voxkeep/modules/*/public.py` for module boundaries.
5. A module's internal implementation only when changing that capability.

`bootstrap/runtime_app.py` is the composition root. It is the only place that should need a
whole-system view.

## Runtime flow

```text
microphone
    |
    v
AudioEngine: capture -> preprocess/audio bus
    | wake_audio            | vad_audio              | asr_audio
    v                       v                        v
wake detector           VAD worker              transcription/FunASR
    | WakeEvent             | VadEvent               | AsrFinalEvent
    +-----------------------+-------------------------+
                            |
                            v
                 unified capture_events queue
                            |
                            v
                     capture worker/FSM
                            |
                      CaptureCommand
                       /           \
                      v             v
            capture_commands     storage_events <---- AsrFinalEvent
                      |             |
                      v             v
                  injection     normalize -> SQLite/JSONL
```

The audio engine is the sole owner of microphone access. It converts raw input to shared
`ProcessedFrame` objects and fans them out to three distinct bounded queues: `wake_audio`,
`vad_audio`, and `asr_audio`. Each consumer receives the frame independently; wake and VAD never
compete for work from the same queue.

Wake, VAD, and final ASR producers publish `WakeEvent`, `VadEvent`, and `AsrFinalEvent` into one
`capture_events` queue. The VAD worker derives speech transitions; `CaptureFSM` combines those
transitions with wake events into a one-shot capture window. Once a sentence has text, capture
emits one `CaptureCommand` to injection and also offers it to storage. Transcription independently
offers each final `AsrFinalEvent` to storage.

VAD can close a sentence before the matching final ASR event reaches the unified queue. Capture
therefore keeps a closed window pending for up to one second and retries transcript extraction as
new events arrive. It emits the command as soon as overlapping final text is available; if the
grace period expires without text, it logs the empty capture and drops that window.

Wake and VAD run in independent threads, so arrival order can differ from event timestamps.
Capture retains recent VAD transitions and replays those at or after a newly arrived wake event.
If the wake is recognized while VAD is already active, capture starts at the wake timestamp. This
keeps a slower wake model from losing the sentence's `speech_start` boundary; the finalized window
still applies the configured `pre_roll_ms` before that synthesized start.

FunASR responses do not always include timestamps. The adapter tracks the span of audio frames
sent since the previous final and uses that span as the fallback, allowing a corrected final that
arrives after `speech_end` to match the pending capture window.

Storage accepts pipeline events rather than database row models. Its worker converts each
`AsrFinalEvent` or `CaptureCommand` into the storage module's internal `StorageRecord`, assigns the
`stream` or `capture` source, and then writes SQLite and optional JSONL. No producer constructs
persistence rows, and storage remains the only module allowed to write SQLite.

## Source layout

| Path | Responsibility |
| --- | --- |
| `bootstrap/` | Runtime construction, start/stop order, and health monitoring |
| `modules/audio_engine/` | Microphone capture, preprocessing, and audio fan-out |
| `modules/capture/` | Wake/VAD detection, capture state, and final command creation |
| `modules/transcription/` | ASR backend adapter and final-event fan-out |
| `modules/injection/` | Desktop injection and action execution |
| `modules/storage/` | Persistence conversion and the SQLite writer |
| `shared/` | Configuration, cross-module events, logging, and queue helpers |
| `cli/` | Operator-facing commands |

The retired `core`, `infra`, and `services` package trees are intentionally absent. New runtime
code belongs in one of the directories above.

## Module boundaries

- A module exposes cross-module builders and types through its `public.py`.
- Other modules must not import its internal `worker`, `contracts`, `application`, `domain`, or
  `infrastructure` files.
- `shared` must not import from `voxkeep.modules`.
- `bootstrap` may depend on module public APIs and shared types to assemble the application.
- Backend failures and fallbacks must be explicit in logs.
- Configuration and event payloads are compatibility boundaries; update tests and docs when they
  intentionally change.

These rules keep navigation predictable without splitting the runtime into separate services or
introducing a dependency-injection framework.

The current cross-module surface is deliberately small:

| Module | Public surface used by composition/runtime code |
| --- | --- |
| `audio_engine` | `build_audio_engine` and the `AudioEngine` lifecycle facade |
| `capture` | `build_capture_detection_workers`, `build_capture_module` |
| `transcription` | `build_transcription_module` |
| `injection` | `build_injection_module` |
| `storage` | `build_storage_module` and the accepted `StorageEvent` union |

Shared cross-module payloads live in `shared/events.py`. Concrete workers and module-owned row
models remain internal even when a public builder returns one of those implementations.

## Concurrency and lifecycle

`AppRuntime` owns queues, components, and stage-specific stop signals. The top-level `max_queue_size`
configuration supplies one capacity for the runtime's bounded queues; there are no capture,
injection, or storage-specific queue-size fields. Producers enqueue without blocking. Most
overflows are warned immediately; audio fan-out records per-consumer drop counters and reports
their totals when the bus stops.

Startup brings consumers online before live audio capture. Shutdown stops and joins one producer
stage at a time: audio, wake/VAD/transcription, capture, then injection/storage. A downstream stage
does not receive its stop signal until every producer feeding it has joined, so a temporarily empty
queue cannot make it exit before late upstream work arrives. Workers that exceed their bounded join
timeout are logged explicitly. The runtime health loop treats an unexpectedly stopped worker as
fatal and initiates shutdown.

Only `modules/audio_engine/infrastructure/audio_capture.py` may open an input device. Only the
storage module may perform SQLite writes. Those ownership constraints are enforced by architecture
tests.

## Supported ASR boundary

The only supported backend is `funasr_ws`, connected to a FunASR 2-pass WebSocket service. VoxKeep
runs on the Linux host; the repository-managed FunASR service runs in Docker. Qwen/vLLM adapters,
configuration, and scripts are not supported and must not be restored.

See [operations.md](operations.md) for deployment and diagnostics, and
[funasr-runtime-baseline.md](funasr-runtime-baseline.md) for protocol details.

## Changing the pipeline

When adding or moving a capability:

1. Define shared event payloads in `shared/events.py` only when they cross module boundaries.
2. Keep implementation inside the owning module.
3. Expose the smallest needed surface from that module's `public.py`.
4. Wire it in `bootstrap/runtime_app.py`.
5. Add focused unit tests plus an integration test when queueing or lifecycle behavior changes.
6. Run `make test-architecture`, then the relevant quality gates from `CONTRIBUTING.md`.
