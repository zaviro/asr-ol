# Graph Report - .  (2026-07-18)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 967 nodes · 1715 edges · 75 communities (55 shown, 20 thin omitted)
- Extraction: 77% EXTRACTED · 23% INFERRED · 0% AMBIGUOUS · INFERRED: 388 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b6d13657`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- load_config
- ProcessedFrame
- AudioBus
- FunAsrWsEngine
- main.py
- Operations
- XdotoolInjector
- test_main.py
- .__init__
- VadEvent
- WorkerSpec
- FakeEngine
- AsrFinalEvent
- FakeWorker
- CaptureCommand
- CaptureWorker
- FunASR Runtime Baseline
- AppConfig
- .__init__
- put_nowait_or_drop
- RuntimeComponents
- _worker
- AppRuntime
- CaptureWindow
- AudioEngine
- TranscriptionWorker
- config_loader.py
- test_resource_boundaries.py
- SqliteStorageWorker
- _runtime_fixture
- FakeExtractor
- build_runtime
- WakeRuleConfig
- PipelineQueues
- AudioEngineConfig
- test_final_shape.py
- Graphify Pipeline
- setup_openwakeword_models.py
- test_events.py
- check_runtime_ai.py
- config_schema.py
- CaptureState
- AsrConfig
- test_module_dependencies.py
- check_env.sh
- test_storage_worker.py
- run_local.sh
- Contributor Quality Gates
- Graph Query Traversal
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- config.py
- __init__.py
- Graphify Git Hooks
- voxkeep

## God Nodes (most connected - your core abstractions)
1. `ProcessedFrame` - 65 edges
2. `AppConfig` - 41 edges
3. `VadEvent` - 38 edges
4. `WakeEvent` - 35 edges
5. `AsrFinalEvent` - 33 edges
6. `FunAsrWsEngine` - 32 edges
7. `load_config()` - 30 edges
8. `CaptureCommand` - 30 edges
9. `CaptureFSM` - 26 edges
10. `CaptureWorker` - 25 edges

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

## Communities (75 total, 20 thin omitted)

### Community 0 - "load_config"
Cohesion: 0.15
Nodes (19): load_config(), Load config from YAML file and environment variables., test_app_config_is_frozen(), test_app_config_validation_rejects_invalid_values(), test_asr_ws_url_uses_ws_or_wss_based_on_ssl(), test_frame_samples_property_is_derived_correctly(), test_load_config_applies_new_asr_env_overrides(), test_load_config_applies_runtime_reconnect_env_overrides() (+11 more)

### Community 1 - "ProcessedFrame"
Cohesion: 0.06
Nodes (39): OpenWakeWordWorker, EnergyVadScorer, _extract_score(), Any, CaptureEvent, Event, Protocol, Queue (+31 more)

### Community 2 - "AudioBus"
Cohesion: 0.05
Nodes (35): AudioBus, Event, Queue, Audio bus for preprocessing and fanout to downstream workers., Preprocess raw chunks once and fan out frames to three pipelines., Initialize queues and lifecycle primitives., Return per-target dropped frame counters., Start the background fanout thread. (+27 more)

### Community 3 - "FunAsrWsEngine"
Cohesion: 0.07
Nodes (26): FunAsrWsEngine, _payload_timestamp(), Any, Queue, FunASR two-pass WebSocket transcription adapter., Track the audio span represented by the next final response., Consume the best local timestamp span for one backend final., Stream microphone PCM to a FunASR WebSocket service. (+18 more)

### Community 4 - "main.py"
Cohesion: 0.06
Nodes (45): Namespace, install_signal_handlers(), Event, Signal handling utilities for graceful runtime shutdown., Install SIGINT/SIGTERM handlers that set the stop event.      Args:         stop, build_arg_parser(), _cmd_backend_doctor(), _cmd_check() (+37 more)

### Community 5 - "Operations"
Cohesion: 0.08
Nodes (22): Architecture, Changing the pipeline, Concurrency and lifecycle, Module boundaries, Reading order, Runtime flow, Source layout, Supported ASR boundary (+14 more)

### Community 6 - "XdotoolInjector"
Cohesion: 0.07
Nodes (32): ABC, Injector, Base injector contract for the injection module., Inject text into the focused target., Contract for text injection backends., build_injector(), Injector backend factory for the injection module., Build the configured injector backend. (+24 more)

### Community 7 - "test_main.py"
Cohesion: 0.09
Nodes (10): _Parser, _RuntimeBase, _RuntimeFatal, _RuntimeHealthy, _RuntimeKeyboard, _setup_common(), test_build_arg_parser_registers_backend_doctor(), test_main_returns_nonzero_on_runtime_fatal() (+2 more)

### Community 8 - ".__init__"
Cohesion: 0.12
Nodes (13): Protocol, Transcript extraction helpers for the capture module., Protocol for transcript accumulation and time-window extraction., Consume one ASR final event., Extract transcript text overlapping the requested time range., TranscriptExtractor, _PendingCapture, CaptureEvent (+5 more)

### Community 9 - "VadEvent"
Cohesion: 0.22
Nodes (19): CaptureFSM, Manage wake-triggered one-sentence capture and one-shot injection., Create FSM timing configuration., Shared event models exchanged by runtime workers., Wake word detection result emitted by wake worker., Voice activity transition emitted by VAD worker., VadEvent, WakeEvent (+11 more)

### Community 10 - "WorkerSpec"
Cohesion: 0.17
Nodes (8): Protocol, Return producer-first stages for lossless downstream draining., Monitor workers until shutdown or a fatal exit., Stop each producer stage, then drain its downstream consumers., Lifecycle shape shared by runtime workers., Name one supervised worker and its shutdown timeout., _Worker, WorkerSpec

### Community 11 - "FakeEngine"
Cohesion: 0.26
Nodes (6): _config(), FakeEngine, _frame(), MonkeyPatch, test_builder_wires_injected_queues_config_and_stop_event(), test_built_worker_runs_engine_and_publishes_direct_final_event()

### Community 12 - "AsrFinalEvent"
Cohesion: 0.13
Nodes (17): InMemoryTranscriptExtractor, Bounded in-memory transcript cache., Create transcript buffer with bounded history., Store finalized transcript segments., Return concatenated text for overlapping finalized segments., build_capture_module(), StorageEvent, Build the capture FSM worker. (+9 more)

### Community 13 - "FakeWorker"
Cohesion: 0.22
Nodes (4): FakeWorker, Event, Exception, Small structural fake for the lifecycle contract.

### Community 14 - "CaptureCommand"
Cohesion: 0.09
Nodes (26): InjectorWorker, Event, Queue, Worker that executes post-capture output actions., Consume capture commands and trigger configured actions., Initialize action worker dependencies., Start the background action execution thread., Join the action worker thread. (+18 more)

### Community 15 - "CaptureWorker"
Cohesion: 0.20
Nodes (6): CaptureWorker, Recover VAD transitions that arrived before a slower wake producer., Turn wake, VAD, and final ASR events into one capture command., Start the capture worker once., Wait for pending events and captures to drain., Report whether the capture thread is running.

### Community 16 - "FunASR Runtime Baseline"
Cohesion: 0.11
Nodes (21): Supported FunASR Path, Modular Monolith Architecture, Module Public API Boundaries, Unreleased Runtime Reliability Changes, Audio Capture Parameters, FunASR WebSocket Configuration, Wake-to-Action Routing, Backend Diagnostics Workflow (+13 more)

### Community 17 - "AppConfig"
Cohesion: 0.23
Nodes (11): Single audio input stream. Callback must remain enqueue-only., SoundDeviceAudioSource, AppConfig, Immutable runtime configuration snapshot., test_audio_source_start_builds_input_stream_with_expected_config(), test_audio_source_start_is_idempotent(), test_audio_source_start_raises_runtime_error_when_sounddevice_missing(), test_audio_source_stop_calls_stream_stop_and_close() (+3 more)

### Community 18 - ".__init__"
Cohesion: 0.13
Nodes (23): _extract_keyword_scores(), _extract_max_score(), _normalize_rules(), NullWakeScorer, OpenWakeWordScorer, Any, CaptureEvent, Event (+15 more)

### Community 19 - "put_nowait_or_drop"
Cohesion: 0.16
Nodes (10): Logger, Any, Queue one preprocessed PCM frame for FunASR., put_nowait_or_drop(), Queue, Queue helper utilities shared across worker implementations., Try to enqueue an item without blocking, and drop it on overflow., T (+2 more)

### Community 21 - "RuntimeComponents"
Cohesion: 0.18
Nodes (9): Build and supervise the complete local audio-to-action pipeline., Signal and workers that can stop after their producers finish., Concrete modules assembled for one runtime instance., Return consumer-first startup order., Create a supervisor around an assembled runtime., Independent stop signals for each producer-to-consumer stage., RuntimeComponents, RuntimeSignals (+1 more)

### Community 22 - "_worker"
Cohesion: 0.25
Nodes (14): LogCaptureFixture, _config(), _event(), FakeEngine, _frame(), CaptureEvent, Queue, StorageEvent (+6 more)

### Community 23 - "AppRuntime"
Cohesion: 0.25
Nodes (5): AppRuntime, Supervise already-assembled runtime components., Return the fatal worker-health error, if one occurred., Return queue depths without exposing queue objects., Start all consumers before live audio production.

### Community 24 - "CaptureWindow"
Cohesion: 0.19
Nodes (5): CaptureWindow, Finalized time window used to extract capture transcript., Advance FSM on VAD boundary and emit finalized window when complete., Advance timeout checks without a new event., FakeFSM

### Community 25 - "AudioEngine"
Cohesion: 0.20
Nodes (7): AudioEngine, Own microphone capture and preprocessing fanout as one runtime component., Return queue sizes owned by the audio engine., Start fanout before opening the microphone stream., Close the microphone, then allow the bus to drain queued audio., Wait for the audio bus to finish draining., Report whether the audio bus is running.

### Community 26 - "TranscriptionWorker"
Cohesion: 0.07
Nodes (21): Protocol, Queue, Internal engine contract for transcription backends., Structural contract for transcription backends., Queue that receives normalized final transcript events., Start engine resources., Submit one processed audio frame., Stop engine resources. (+13 more)

### Community 27 - "config_loader.py"
Cohesion: 0.26
Nodes (10): _apply_env(), _deep_merge(), _load_yaml(), _parse_wake_rules(), Any, Path, Configuration loading and merge helpers., Reject YAML keys that are absent from the default configuration shape. (+2 more)

### Community 28 - "test_resource_boundaries.py"
Cohesion: 0.38
Nodes (10): _calls_in(), _find_calls(), _import_aliases(), _local_aliases(), AST, Path, _qualified_name(), Resolve simple assignments such as ``audio = pyaudio.PyAudio()``. (+2 more)

### Community 29 - "SqliteStorageWorker"
Cohesion: 0.06
Nodes (29): Internal storage records and accepted persistence events., Normalized row written by the storage worker., StorageRecord, _normalize_event(), Event, Queue, StorageEvent, SQLite-backed storage worker for ASR and capture records. (+21 more)

### Community 30 - "_runtime_fixture"
Cohesion: 0.40
Nodes (8): FakeAudio, _runtime_fixture(), test_run_forever_exits_cleanly_after_external_shutdown(), test_run_forever_reports_every_dead_worker(), test_runtime_components_define_readable_lifecycle_plans(), test_runtime_propagates_audio_start_failure_and_signals_shutdown(), test_runtime_queue_sizes_combine_audio_and_pipeline_queues(), test_runtime_starts_and_stops_components_once_in_dependency_order()

### Community 31 - "FakeExtractor"
Cohesion: 0.36
Nodes (7): _capture_config(), FakeExtractor, Queue, StorageEvent, test_capture_worker_routes_action_by_keyword(), test_storage_receives_capture_only_after_command_enqueue_succeeds(), _worker()

### Community 32 - "build_runtime"
Cohesion: 0.22
Nodes (7): build_runtime(), Event, Expose the operator-facing shutdown request signal., Create queues, module workers, and their lifecycle supervisor., Create an unset signal for every shutdown stage., MonkeyPatch, test_build_runtime_connects_each_consumer_to_the_audio_fanout()

### Community 33 - "WakeRuleConfig"
Cohesion: 0.25
Nodes (7): Wake keyword routing rule., Return wake rules currently enabled., WakeRuleConfig, test_app_config_rejects_duplicate_wake_keywords(), test_app_config_rejects_empty_wake_action(), test_app_config_rejects_empty_wake_keyword(), test_enabled_wake_rules_filters_disabled_rules()

### Community 34 - "PipelineQueues"
Cohesion: 0.29
Nodes (5): PipelineQueues, All bounded queues that connect runtime modules., Create every pipeline queue with one shared capacity., Return externally meaningful queue depths., test_pipeline_queues_are_distinct_and_bounded()

### Community 35 - "AudioEngineConfig"
Cohesion: 0.29
Nodes (4): Queue, AudioEngineConfig, Audio engine specific configuration., Return frame size in samples.

### Community 38 - "test_final_shape.py"
Cohesion: 0.33
Nodes (9): _imported_names(), _legacy_import_violations(), _legacy_runtime_files(), _module_name_for(), AST, Path, test_bootstrap_does_not_import_legacy_layers(), test_repository_has_no_legacy_runtime_files() (+1 more)

### Community 39 - "Graphify Pipeline"
Cohesion: 0.18
Nodes (11): Folder Watcher, URL Ingestion, Graph Export Formats, Extraction Confidence Rubric, Cross-Repository Graph Merge, Whisper Media Transcription, Incremental Graph Update, Graphify Pipeline (+3 more)

### Community 40 - "setup_openwakeword_models.py"
Cohesion: 0.31
Nodes (10): _build_parser(), _download_url_with_retries(), main(), ArgumentParser, Path, Download and verify openwakeword ONNX assets used by runtime-ai mode., Prepare openwakeword assets and validate ONNX inference., _resolve_model_names() (+2 more)

### Community 42 - "test_events.py"
Cohesion: 0.25
Nodes (7): test_asr_final_event_fields(), test_capture_command_slots(), test_processed_frame_slots(), test_raw_audio_chunk_slots(), test_vad_event_speech_end(), test_vad_event_speech_start(), test_wake_event_slots()

### Community 44 - "check_runtime_ai.py"
Cohesion: 0.36
Nodes (8): _check_module(), _check_openwakeword_onnx(), _check_silero_runtime(), main(), _print_result(), Runtime AI dependency and model readiness checks., Run runtime-AI diagnostics and return process exit code., _resolve_wake_models()

### Community 45 - "config_schema.py"
Cohesion: 0.36
Nodes (7): Configuration dataclasses and validation helpers., Validate configuration values after dataclass construction., _require_non_negative_int(), _require_positive_float(), _require_positive_int(), _require_probability(), _validate_wake_rules()

### Community 46 - "CaptureState"
Cohesion: 0.18
Nodes (9): Enum, _CaptureSession, CaptureState, Wake-triggered one-sentence capture state machine., Finite states for one-shot capture orchestration., Mutable in-flight capture session state., Return current FSM state., Advance FSM on wake detection. (+1 more)

### Community 47 - "AsrConfig"
Cohesion: 0.15
Nodes (10): AsrConfig, CaptureConfig, InjectorConfig, ASR specific configuration., Return websocket endpoint URL., Audio capture and VAD/Wake specific configuration., Storage specific configuration., Text injector specific configuration. (+2 more)

### Community 48 - "test_module_dependencies.py"
Cohesion: 0.36
Nodes (9): _find_bootstrap_module_import_violations(), _find_import_violations(), _imported_names(), _module_name_for(), AST, Path, Find bootstrap imports that bypass a module's public boundary., test_bootstrap_only_imports_module_public_apis() (+1 more)

### Community 50 - "check_env.sh"
Cohesion: 0.70
Nodes (4): mark_fail(), mark_pass(), run_python(), check_env.sh script

### Community 51 - "test_storage_worker.py"
Cohesion: 0.33
Nodes (9): Row, _asr(), _assert_utc_timestamp(), _capture(), _count_rows(), Path, _stored_rows(), test_storage_worker_flushes_on_batch_size_without_stop() (+1 more)

### Community 52 - "run_local.sh"
Cohesion: 0.83
Nodes (3): compose(), run_local.sh script, wait_for_funasr()

### Community 53 - "Contributor Quality Gates"
Cohesion: 0.67
Nodes (3): Python 3.11 uv Validation, Contributor Quality Gates, Pre-commit Quality Gates

## Knowledge Gaps
- **34 isolated node(s):** `voxkeep`, `Reading order`, `Runtime flow`, `Source layout`, `Module boundaries` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ProcessedFrame` connect `ProcessedFrame` to `AudioBus`, `PipelineQueues`, `FunAsrWsEngine`, `VadEvent`, `WorkerSpec`, `FakeEngine`, `test_events.py`, `.__init__`, `put_nowait_or_drop`, `RuntimeComponents`, `_worker`, `AppRuntime`, `AudioEngine`, `TranscriptionWorker`, `SqliteStorageWorker`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `AppConfig` to `build_runtime`, `load_config`, `AudioBus`, `FunAsrWsEngine`, `WakeRuleConfig`, `XdotoolInjector`, `AsrFinalEvent`, `config_schema.py`, `CaptureCommand`, `AsrConfig`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `CaptureCommand` connect `CaptureCommand` to `PipelineQueues`, `.__init__`, `VadEvent`, `WorkerSpec`, `test_events.py`, `AsrFinalEvent`, `CaptureWorker`, `test_storage_worker.py`, `RuntimeComponents`, `AppRuntime`, `CaptureWindow`, `SqliteStorageWorker`, `FakeExtractor`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `ProcessedFrame` (e.g. with `AppRuntime` and `PipelineQueues`) actually correct?**
  _`ProcessedFrame` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `VadEvent` (e.g. with `CaptureFSM` and `_CaptureSession`) actually correct?**
  _`VadEvent` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `WakeEvent` (e.g. with `CaptureFSM` and `_CaptureSession`) actually correct?**
  _`WakeEvent` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `AsrFinalEvent` (e.g. with `InMemoryTranscriptExtractor` and `TranscriptExtractor`) actually correct?**
  _`AsrFinalEvent` has 23 INFERRED edges - model-reasoned connections that need verification._
