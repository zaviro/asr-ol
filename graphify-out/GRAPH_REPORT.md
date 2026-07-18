# Graph Report - .  (2026-07-18)

## Corpus Check
- Corpus is ~49,403 words - fits in a single context window. You may not need a graph.

## Summary
- 1176 nodes · 2048 edges · 111 communities (68 shown, 43 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 481 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- openwakeword worker py
- OpenWakeWordWorker
- audio bus py
- funasr ws py
- shutdown py
- runtime status py
- factory py
- test main py
- asr health py
- CaptureSession
- FakeStorageModule
- backend events py
- transcript extractor py
- test runtime app py
- InjectorWorker
- normalize backend event
- Reusable uv Setup Action
- Create queues components workers and
- WorkerCaptureModule
- InjectionModule
- DetectionWorker
- interfaces py
- test asr worker py
- runtime app py
- CaptureWindow
- build storage module
- contracts py
- CaptureModule
- Subscribe to capture completion events
- sqlite storage worker py
- StorageModule
- TranscriptionModule
- asr assets py
- lifecycle py
- SqliteStorageModule
- base py
- asr backends py
- WorkerInjectionModule
- test final shape py
- Graphify Pipeline
- setup openwakeword models py
- FakeCaptureModule
- test events py
- engine factory py
- check runtime ai py
- config schema py
- capture fsm py
- AudioEngineConfig
- test module dependencies py
- Modular Monolith Refactor Design
- check env sh
- test storage worker py
- run local sh
- Pre commit Quality Gates
- Local ASR Injector MVP Design
- Audio Engine Rename Design
- config env py
- Graph Query Traversal
- Local Always On ASR Injector
- UV Layered Structure Refactor Design
- Project Hardening Design
- Runtime Boundary Cleanup Design
- ASR Backend and Asset Management
- Runtime status data model helpers
- Bootstrap composition root package
- Command line entrypoints for voxkeep
- Core contracts events and configuration
- ASR infrastructure adapters
- Infrastructure adapters for audio ASR
- Storage infrastructure adapters
- Runtime infrastructure adapters
- Runtime module public package
- Application services for the capture
- contracts py
- Domain types and state machines
- Infrastructure adapters for the capture
- Capture module public package
- Top level business modules for
- Application services for the injection
- Infrastructure adapters for the injection
- Start the background action execution
- Injection module public package
- Application services for the storage
- contracts py
- Infrastructure adapters for the storage
- Storage module public package
- Application services for the transcription
- Infrastructure adapters for the transcription
- Transcription module public package
- Runtime orchestration services for the
- config py
- config defaults py
- Stable shared utilities for cross
- Graphify Git Hooks
- Project Onboarding Map
- VoxKeep Rename Plan
- Synchronous Threaded Model ADR
- voxkeep

## God Nodes (most connected - your core abstractions)
1. `AppConfig` - 64 edges
2. `ProcessedFrame` - 64 edges
3. `AppRuntime` - 47 edges
4. `AsrFinalEvent` - 47 edges
5. `WakeEvent` - 40 edges
6. `VadEvent` - 40 edges
7. `CaptureCommand` - 35 edges
8. `FunAsrWsEngine` - 30 edges
9. `WorkerCaptureModule` - 29 edges
10. `StorageRecord` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_worker_with_no_enabled_rules_emits_nothing()` --calls--> `OpenWakeWordWorker`  [INFERRED]
  tests/unit/modules/capture/test_openwakeword_scorer.py → src/voxkeep/modules/capture/infrastructure/openwakeword_worker.py
- `test_raw_audio_chunk_slots()` --calls--> `RawAudioChunk`  [INFERRED]
  tests/unit/shared/test_events.py → src/voxkeep/shared/events.py
- `test_processed_frame_slots()` --calls--> `ProcessedFrame`  [INFERRED]
  tests/unit/shared/test_events.py → src/voxkeep/shared/events.py
- `test_wake_event_slots()` --calls--> `WakeEvent`  [INFERRED]
  tests/unit/shared/test_events.py → src/voxkeep/shared/events.py
- `test_vad_event_speech_end()` --calls--> `VadEvent`  [INFERRED]
  tests/unit/shared/test_events.py → src/voxkeep/shared/events.py

## Import Cycles
- None detected.

## Communities (111 total, 43 thin omitted)

### Community 0 - "openwakeword worker py"
Cohesion: 0.06
Nodes (53): _extract_keyword_scores(), _extract_max_score(), _normalize_rules(), NullWakeScorer, OpenWakeWordScorer, Any, Event, Protocol (+45 more)

### Community 1 - "OpenWakeWordWorker"
Cohesion: 0.08
Nodes (32): OpenWakeWordWorker, EnergyVadScorer, _extract_score(), Any, Event, Protocol, Queue, Best-effort Silero VAD adapter; falls back to energy scorer on runtime errors. (+24 more)

### Community 2 - "audio bus py"
Cohesion: 0.06
Nodes (31): Logger, AudioBus, Event, Queue, Audio bus for preprocessing and fanout to downstream workers., Preprocess raw chunks once and fan out frames to three pipelines., Initialize queues and lifecycle primitives., Return per-target dropped frame counters. (+23 more)

### Community 3 - "funasr ws py"
Cohesion: 0.08
Nodes (23): FunAsrWsEngine, Any, Event, Queue, FunASR two-pass WebSocket transcription adapter., Stream microphone PCM to a FunASR WebSocket service., Initialize bounded queues and lifecycle state., Return the queue receiving finalized transcript events. (+15 more)

### Community 4 - "shutdown py"
Cohesion: 0.08
Nodes (37): Namespace, install_signal_handlers(), Event, Signal handling utilities for graceful runtime shutdown., Install SIGINT/SIGTERM handlers that set the stop event.      Args:         stop, _asset_status_from_state(), build_arg_parser(), _cmd_asset_status() (+29 more)

### Community 5 - "runtime status py"
Cohesion: 0.07
Nodes (29): collect_runtime_status(), collect_runtime_status_dict(), EventLike, Any, Protocol, _queue_size(), QueueLike, Runtime status collection helpers for diagnostics and future APIs. (+21 more)

### Community 6 - "factory py"
Cohesion: 0.08
Nodes (27): build_injector(), Injector backend factory for the injection module., Build the configured injector backend., X11 injector implementation backed by xdotool., Inject text under X11 using xdotool., Create injector with xdotool timing options., Inject text and optional Enter keypress., XdotoolInjector (+19 more)

### Community 7 - "test main py"
Cohesion: 0.08
Nodes (10): _Parser, _RuntimeBase, _RuntimeFatal, _RuntimeHealthy, _RuntimeKeyboard, _setup_common(), test_build_arg_parser_registers_backend_and_asset_groups(), test_main_returns_nonzero_on_runtime_fatal() (+2 more)

### Community 8 - "asr health py"
Cohesion: 0.12
Nodes (28): AsrHealthStatus, classify_backend_health(), classify_health_result(), normalize_asset_status(), normalize_health_state(), probe_websocket_handshake(), Normalized ASR backend health helpers., Classify a backend probe into a normalized health status. (+20 more)

### Community 9 - "CaptureSession"
Cohesion: 0.17
Nodes (23): CaptureFSM, _CaptureSession, Mutable in-flight capture session state., Manage wake-triggered one-sentence capture and one-shot injection., Create FSM timing configuration., Advance FSM on wake detection., Shared event models exchanged by runtime workers., Wake word detection result emitted by wake worker. (+15 more)

### Community 10 - "FakeStorageModule"
Cohesion: 0.10
Nodes (10): _FakeInjectionModule, _FakeStorageModule, _FakeTranscriptionModule, test_runtime_builds_capture_through_module_public_api(), test_runtime_builds_funasr_transcription_backend_through_public_api(), test_runtime_builds_injection_through_module_public_api(), test_runtime_builds_storage_through_module_public_api(), test_runtime_builds_worker_lifecycle_plan() (+2 more)

### Community 11 - "backend events py"
Cohesion: 0.13
Nodes (14): BackendTranscriptEvent, Backend-neutral transcript events produced by transcription engines., Normalized transcript event emitted by a transcription backend., Return whether the backend event represents a final transcript., build_transcription_module(), Build the transcription module public entrypoint., _FakeEngine, test_backend_transcript_event_marks_final_events() (+6 more)

### Community 12 - "transcript extractor py"
Cohesion: 0.11
Nodes (16): InMemoryTranscriptExtractor, Protocol, Transcript extraction helpers for the capture module., Protocol for transcript accumulation and time-window extraction., Consume one ASR final event., Extract transcript text overlapping the requested time range., Bounded in-memory transcript cache., Create transcript buffer with bounded history. (+8 more)

### Community 13 - "test runtime app py"
Cohesion: 0.13
Nodes (11): _AudioSourceFailure, _AudioSourceRecorder, _CallRecorder, _FakeWorker, _patch_runtime_ai_worker_builders(), test_find_unhealthy_workers_returns_all_dead_workers(), test_run_forever_raises_when_worker_is_unhealthy(), test_runtime_builds_runtime_ai_workers_through_builder_functions() (+3 more)

### Community 14 - "InjectorWorker"
Cohesion: 0.15
Nodes (14): Exception, InjectorWorker, Consume capture commands and trigger configured actions., Join the action worker thread., Return whether the action worker thread is alive., Execute one capture command through the configured output path., FakeInjector, test_execute_action_returns_false_for_unknown_action() (+6 more)

### Community 15 - "normalize backend event"
Cohesion: 0.11
Nodes (12): _normalize_backend_event(), Queue, Public entrypoints for the transcription module., Subscribe to final transcript events., Join worker thread and engine., Report whether the worker thread is alive., Normalize one backend transcript event into the shared ASR event type., Transcription module that streams audio to ASR backend and fans out results. (+4 more)

### Community 16 - "Reusable uv Setup Action"
Cohesion: 0.11
Nodes (21): Supported FunASR Path, Modular Monolith Architecture, Module Public API Boundaries, Unreleased Runtime Reliability Changes, Audio Capture Parameters, FunASR WebSocket Configuration, Wake-to-Action Routing, Backend Diagnostics Workflow (+13 more)

### Community 17 - "Create queues components workers and"
Cohesion: 0.16
Nodes (13): Create queues, components, workers, and lifecycle plans., Queue, Single audio input stream. Callback must remain enqueue-only., SoundDeviceAudioSource, AppConfig, Immutable runtime configuration snapshot., test_audio_source_start_builds_input_stream_with_expected_config(), test_audio_source_start_is_idempotent() (+5 more)

### Community 18 - "WorkerCaptureModule"
Cohesion: 0.10
Nodes (10): Start the capture module background thread., Expose a symmetric lifecycle hook for the runtime module., Join the background thread., Report whether the background thread is alive., Accept one wake detection event., Accept one VAD boundary event., Accept one transcript event., Capture module that runs wake-triggered capture orchestration in a background th (+2 more)

### Community 19 - "InjectionModule"
Cohesion: 0.11
Nodes (15): build_injection_module(), InjectionModule, Event, Protocol, Queue, Public entrypoints for the injection module., Public API exposed by the injection module., Start module resources. (+7 more)

### Community 20 - "DetectionWorker"
Cohesion: 0.14
Nodes (14): build_capture_detection_workers(), build_capture_module(), DetectionWorker, Event, Protocol, Queue, Public entrypoints for the capture module., Build the capture module public entrypoint. (+6 more)

### Community 21 - "interfaces py"
Cohesion: 0.12
Nodes (12): ASREngine, AudioSource, ABC, Shared abstract interfaces for pluggable runtime components., Define the ASR engine lifecycle and streaming contract., Start engine resources and background I/O., Submit one preprocessed audio frame for recognition., Close engine resources and flush pending work. (+4 more)

### Community 22 - "test asr worker py"
Cohesion: 0.30
Nodes (13): _backend_event(), FakeEngine, _frame(), _make_module(), Event, Queue, test_drain_final_events_fanout_and_storage_policy(), test_drain_final_events_ignores_backend_partial_events() (+5 more)

### Community 23 - "runtime app py"
Cohesion: 0.13
Nodes (9): AppRuntime, Application runtime composition root and lifecycle orchestration., Return fatal runtime error message when one has occurred., Start all workers and audio capture in dependency-safe order., Block until shutdown while monitoring worker health., Trigger graceful shutdown and join all workers., Assemble and coordinate the full audio-to-action runtime pipeline., _FakeInjector (+1 more)

### Community 24 - "CaptureWindow"
Cohesion: 0.15
Nodes (7): CaptureWindow, Finalized time window used to extract capture transcript., Advance FSM on VAD boundary and emit finalized window when complete., Advance timeout checks without a new event., FakeExtractor, FakeFSM, test_capture_worker_routes_action_by_keyword()

### Community 25 - "build storage module"
Cohesion: 0.16
Nodes (14): build_storage_module(), Event, Queue, Public entrypoints for the storage module., Build the storage module public entrypoint., Create a storage module backed by the SQLite worker., Event, Create transcription module dependencies and engine. (+6 more)

### Community 26 - "contracts py"
Cohesion: 0.13
Nodes (12): Protocol, Queue, Public contracts for the transcription module., Structural contract for transcription backends., Queue that receives backend transcript events., Start engine resources., Submit one processed audio frame., Stop engine resources. (+4 more)

### Community 27 - "CaptureModule"
Cohesion: 0.12
Nodes (9): CaptureModule, Public API exposed by the capture module., Start module resources., Stop module resources., Accept one wake detection event., Accept one VAD boundary event., Accept one transcript event., Join module resources. (+1 more)

### Community 28 - "Subscribe to capture completion events"
Cohesion: 0.15
Nodes (11): Subscribe to capture completion events., Subscribe to capture completion events., InjectionResult, Public contracts for the injection module., Result returned by injection-side command execution., Execute the configured output action for a capture event., CaptureCommand, Final capture output that triggers downstream action. (+3 more)

### Community 29 - "sqlite storage worker py"
Cohesion: 0.13
Nodes (9): Event, Queue, SQLite-backed storage worker for ASR and capture records., Persist storage records to SQLite and optional JSONL debug stream., Initialize worker with batching and flush policies., Return number of records written by this worker., Start background storage thread once., Return whether storage thread is currently alive. (+1 more)

### Community 30 - "StorageModule"
Cohesion: 0.13
Nodes (9): Protocol, Public API exposed by the storage module., Start module resources., Stop module resources., Join module worker resources., Return whether module worker resources are alive., Convert one transcript event into a storage write request., Convert one capture event into a storage write request. (+1 more)

### Community 31 - "TranscriptionModule"
Cohesion: 0.13
Nodes (9): Protocol, Public API exposed by the transcription module., Start module resources., Stop module resources., Submit one audio frame into the transcription pipeline., Subscribe to final transcript events., Join module resources., Report whether module resources are alive. (+1 more)

### Community 32 - "asr assets py"
Cohesion: 0.20
Nodes (11): assets_state_path(), Any, Path, Persistent ASR backend asset state helpers., Return the user-data path that stores backend installation state., Read the persisted backend asset state, returning an empty mapping when absent., Persist backend asset state under the user data directory., read_assets_state() (+3 more)

### Community 33 - "lifecycle py"
Cohesion: 0.15
Nodes (9): Protocol, Lifecycle abstractions for runtime worker management., Define the minimal runtime worker lifecycle contract., Start worker resources and background processing., Block until worker exits or timeout is reached., Report whether the worker background task is still running., Bind a worker to a logical name and shutdown timeout., Worker (+1 more)

### Community 34 - "SqliteStorageModule"
Cohesion: 0.14
Nodes (8): Public storage module backed by the legacy SQLite worker., Start the underlying storage worker., Expose a symmetric lifecycle hook for the runtime module., Join the underlying storage worker., Report whether the underlying worker thread is alive., Convert a transcript event into a storage write request., Convert a capture event into a storage write request., SqliteStorageModule

### Community 35 - "base py"
Cohesion: 0.17
Nodes (9): Injector, ABC, Base injector contract for the injection module., Inject text into the focused target., Contract for text injection backends., Event, Queue, Worker that executes post-capture output actions. (+1 more)

### Community 36 - "asr backends py"
Cohesion: 0.23
Nodes (11): AsrBackendDefinition, Built-in ASR backend registry., Describe one built-in ASR backend., Return the registered backend definition for ``backend_id``., resolve_backend_definition(), test_builtin_backend_has_correct_attributes(), test_builtin_registry_contains_funasr_ws(), test_resolve_backend_definition_normalizes_input() (+3 more)

### Community 37 - "WorkerInjectionModule"
Cohesion: 0.17
Nodes (7): Public injection module backed by the legacy worker implementation., Start the underlying injection worker., Expose a symmetric lifecycle hook for the runtime module., Join the underlying injection worker., Report whether the underlying worker thread is alive., Execute one capture event through the configured output action., WorkerInjectionModule

### Community 38 - "test final shape py"
Cohesion: 0.30
Nodes (11): _import_violations_for_prefix(), _imported_names(), _legacy_import_violations(), _legacy_runtime_files(), _module_name_for(), AST, Path, test_bootstrap_does_not_import_capture_internals() (+3 more)

### Community 39 - "Graphify Pipeline"
Cohesion: 0.18
Nodes (11): Folder Watcher, URL Ingestion, Graph Export Formats, Extraction Confidence Rubric, Cross-Repository Graph Merge, Whisper Media Transcription, Incremental Graph Update, Graphify Pipeline (+3 more)

### Community 40 - "setup openwakeword models py"
Cohesion: 0.31
Nodes (10): _build_parser(), _download_url_with_retries(), main(), ArgumentParser, Path, Download and verify openwakeword ONNX assets used by runtime-ai mode., Prepare openwakeword assets and validate ONNX inference., _resolve_model_names() (+2 more)

### Community 42 - "test events py"
Cohesion: 0.18
Nodes (10): test_asr_final_event_can_be_non_final(), test_asr_final_event_defaults_to_final(), test_capture_command_slots(), test_processed_frame_slots(), test_raw_audio_chunk_slots(), test_storage_record_with_meta(), test_storage_record_without_meta(), test_vad_event_speech_end() (+2 more)

### Community 43 - "engine factory py"
Cohesion: 0.24
Nodes (8): build_asr_engine(), _build_funasr_ws_engine(), Event, Factory for constructing transcription engines., Build the configured ASR engine., AsrConfig, ASR specific configuration., Return websocket endpoint URL.

### Community 44 - "check runtime ai py"
Cohesion: 0.36
Nodes (8): _check_module(), _check_openwakeword_onnx(), _check_silero_runtime(), main(), _print_result(), Runtime AI dependency and model readiness checks., Run runtime-AI diagnostics and return process exit code., _resolve_wake_models()

### Community 45 - "config schema py"
Cohesion: 0.36
Nodes (7): Configuration dataclasses and validation helpers., Validate configuration values after dataclass construction., _require_non_negative_int(), _require_positive_float(), _require_positive_int(), _require_probability(), _validate_wake_rules()

### Community 46 - "capture fsm py"
Cohesion: 0.29
Nodes (6): Enum, CaptureState, Wake-triggered one-sentence capture state machine., Finite states for one-shot capture orchestration., Return current FSM state., str

### Community 47 - "AudioEngineConfig"
Cohesion: 0.29
Nodes (4): AudioEngineConfig, Audio engine specific configuration., Return frame size in samples., app_config()

### Community 48 - "test module dependencies py"
Cohesion: 0.48
Nodes (6): _find_import_violations(), _imported_names(), _module_name_for(), AST, Path, test_module_boundaries_only_allow_public_cross_module_imports()

### Community 49 - "Modular Monolith Refactor Design"
Cohesion: 0.40
Nodes (5): Modular Monolith Refactor Design, Modular Monolith Refactor Plan, Modular Monolith Final Shape Design, Modular Monolith Final Shape Plan, Eliminate Legacy Worker Wrapper

### Community 50 - "check env sh"
Cohesion: 0.70
Nodes (4): mark_fail(), mark_pass(), run_python(), check_env.sh script

### Community 51 - "test storage worker py"
Cohesion: 0.80
Nodes (4): _count_rows(), _record(), test_storage_worker_flushes_on_batch_size_without_stop(), test_storage_worker_persists_records_on_stop_flush()

### Community 52 - "run local sh"
Cohesion: 0.83
Nodes (3): compose(), run_local.sh script, wait_for_funasr()

### Community 53 - "Pre commit Quality Gates"
Cohesion: 0.67
Nodes (3): Python 3.11 uv Validation, Contributor Quality Gates, Pre-commit Quality Gates

### Community 54 - "Local ASR Injector MVP Design"
Cohesion: 0.67
Nodes (3): Local ASR Injector MVP Design, ASR Local Injector Implementation Plan, MVP Acceptance Checklist

### Community 55 - "Audio Engine Rename Design"
Cohesion: 0.67
Nodes (3): Audio Engine Rename Design, Module-Centric Config Decomposition Design, Config Decomposition and Audio Engine Rename Plan

## Knowledge Gaps
- **35 isolated node(s):** `voxkeep`, `Structural AST Extraction`, `URL Ingestion`, `Folder Watcher`, `Graph Export Formats` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **43 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppRuntime` connect `runtime app py` to `lifecycle py`, `audio bus py`, `OpenWakeWordWorker`, `shutdown py`, `CaptureSession`, `FakeCaptureModule`, `FakeStorageModule`, `transcript extractor py`, `test runtime app py`, `Create queues components workers and`, `build storage module`, `Subscribe to capture completion events`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Why does `ProcessedFrame` connect `OpenWakeWordWorker` to `openwakeword worker py`, `audio bus py`, `funasr ws py`, `CaptureSession`, `test events py`, `backend events py`, `normalize backend event`, `WorkerCaptureModule`, `DetectionWorker`, `interfaces py`, `test asr worker py`, `runtime app py`, `build storage module`, `contracts py`, `CaptureModule`, `TranscriptionModule`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `Create queues components workers and` to `openwakeword worker py`, `funasr ws py`, `factory py`, `FakeCaptureModule`, `FakeStorageModule`, `backend events py`, `test runtime app py`, `config schema py`, `AudioEngineConfig`, `DetectionWorker`, `test asr worker py`, `build storage module`, `Subscribe to capture completion events`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `ProcessedFrame` (e.g. with `AppRuntime` and `AudioBus`) actually correct?**
  _`ProcessedFrame` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `AppRuntime` (e.g. with `AudioBus` and `SoundDeviceAudioSource`) actually correct?**
  _`AppRuntime` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `AsrFinalEvent` (e.g. with `AppRuntime` and `InMemoryTranscriptExtractor`) actually correct?**
  _`AsrFinalEvent` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `WakeEvent` (e.g. with `AppRuntime` and `CaptureFSM`) actually correct?**
  _`WakeEvent` has 28 INFERRED edges - model-reasoned connections that need verification._
