# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Architecture tests for module public APIs, microphone ownership, and SQLite ownership.
- Current architecture and operations guides.
- Late-ASR capture grace and VAD-history replay for producer ordering differences.

### Changed

- Runtime wiring now uses distinct wake, VAD, and ASR audio queues plus one capture-event queue.
- Shutdown drains audio, analysis, capture, and output stages in producer-to-consumer order.
- Module `public.py` files are thin composition boundaries; capture and transcription workers live
  in dedicated implementation modules.
- Configuration defaults, environment overrides, and loading are consolidated; YAML keys are
  validated recursively and the top-level `max_queue_size` controls all bounded runtime queues.
- Storage accepts pipeline events and owns normalization into its SQLite/JSONL record format.
- FunASR WebSocket is the only supported ASR backend.

### Fixed

- Wake and VAD no longer compete for frames from the same queue.
- Capture recovers when VAD events arrive before a slower wake result or final ASR arrives after
  the VAD close event.
- FunASR shutdown sends the final speaking marker, waits for corrected final text, and preserves
  local audio-span timestamps when the backend omits them.
- Partial runtime startup rolls back cleanly, and downstream workers cannot exit before upstream
  queues have drained.

### Removed

- Retired `core`, `infra`, `services`, `api`, `agents`, and `tools` runtime package trees.
- The backend asset-state registry, `asset status`, `backend list`, and `backend current` commands.
- Single-backend registries/factories, deep-import wrapper contracts, and unused runtime status API.
- Obsolete `wake.threshold`, `storage.store_final_only`, and module-specific queue-size settings.
- Historical implementation-plan documents that no longer describe the active system.
