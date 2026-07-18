# Contributing

## Setup

Install Python 3.11 and `uv`, then sync the development environment:

```bash
make sync
```

Runtime, audio, wake, or VAD work also needs the AI dependencies and model assets:

```bash
make setup-ai-models
make validate-config
```

Run all project Python commands through `uv`; do not depend on a system Python or an activated
shell environment. `make doctor` includes a live FunASR handshake, so run it only after the
configured backend is reachable.

## Before changing code

Read [docs/architecture.md](docs/architecture.md). Keep changes inside the module that owns the
behavior, and expose cross-module dependencies through that module's `public.py`.

The following boundaries are non-negotiable:

- Do not recreate runtime code under `core`, `infra`, or `services`.
- Cross-module imports under `modules` must target the owning module's `public.py`; worker,
  domain, application, contracts, and infrastructure files are internal.
- `shared` must not import from `voxkeep.modules`.
- Only `modules/audio_engine/infrastructure/audio_capture.py` may open microphones.
- Only the storage module may write SQLite.
- The supported ASR path is `funasr_ws`; do not restore Qwen/vLLM code or configuration.
- Update tests and docs with intentional config, event, CLI, wake, or action semantic changes.

## Quality gates

Use the fast loop while editing:

```bash
make fmt
make lint
make typecheck
make test-fast
```

Before opening a PR, run the repository quality gates:

```bash
make precommit
make typecheck
make test
make validate-config
```

Run `make test-integration` for worker coordination, queues, lifecycle, or runtime wiring. Run
`make test-e2e` when CLI behavior or an end-to-end integration changes. Tests requiring real
hardware or external services remain opt-in.

For a single command that runs the standard developer checks:

```bash
make cli-check
```

## Testing style

- Put pure logic, state machines, and narrow adapters in `tests/unit`.
- Put dependency and package-boundary checks in `tests/architecture`.
- Put threaded pipeline and shutdown behavior in `tests/integration`.
- Put CLI and complete external flows in `tests/e2e`.
- Prefer observable behavior over tests that mirror private implementation structure.

## Runtime diagnostics

When a local runtime check fails, start with:

```bash
make doctor
uv run --python 3.11 python -m voxkeep backend doctor --config config/config.yaml
```

Deployment and troubleshooting details are in [docs/operations.md](docs/operations.md).

## Commits and pull requests

Use focused Conventional Commits such as `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, and
`chore:`. A pull request should include:

- The behavior and rationale for the change.
- Commands run and their outcomes.
- Any impact on configuration, endpoints, audio devices, wake models, injection, or persistence.
