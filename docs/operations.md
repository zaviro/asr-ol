# Operations

This guide covers the supported local Linux setup: VoxKeep runs on the host and connects to a
FunASR 2-pass WebSocket service, normally managed with the repository's Docker Compose file.

## Prerequisites

- Python 3.11 and `uv`
- Docker with the Compose plugin
- A working PipeWire/PulseAudio input visible through `pactl`
- `xdotool` on X11, or `ydotool` and `ydotoold` on Wayland

Install the project, AI runtime dependencies, and wake-word models:

```bash
make setup-ai-models
```

`make setup-ai-models` depends on `make sync-ai`, so it also installs the development and runtime
AI dependencies. All Python commands in this repository must run through `uv` with Python 3.11.

## Start the managed runtime

Validate the configuration first:

```bash
make validate-config
```

Then start VoxKeep:

```bash
make run
```

`make run` starts the Compose `funasr` service, waits until its TCP endpoint is reachable, and
then starts VoxKeep on the host. The first run may download the container image and initialize
models in the `funasr-models` volume; the default wait limit is 600 seconds.

`make doctor` checks the desktop, microphone, AI dependencies, injection tools, and a live FunASR
WebSocket handshake. Run it after the backend is reachable, for example from another terminal
after starting the service. It is expected to fail when FunASR is offline. To complete diagnostics
before starting VoxKeep, run `make funasr-up`, wait for server initialization, then run
`make doctor` followed by `make run`.

Useful service commands:

```bash
make funasr-up
make funasr-logs
make funasr-down
```

## FunASR deployment facts

- Configured backend: `funasr_ws`
- Default host endpoint: `ws://127.0.0.1:10096/`
- Container listener: unencrypted WebSocket on port `10095`
- Default image: `funasr-runtime-sdk-online-cpu-0.1.13`
- Model volume: `funasr-models` mounted at `/workspace/models`

Compose binds the service to loopback, mapping host port `10096` to container port `10095`.
VoxKeep uses 16 kHz mono signed 16-bit PCM and reframes its internal 32 ms audio frames to the
FunASR protocol's expected chunks. See [funasr-runtime-baseline.md](funasr-runtime-baseline.md)
for the exact client exchange.

Qwen/vLLM is not a supported backend. Do not add Qwen configuration, adapters, scripts, or
fallback behavior when diagnosing FunASR.

## Use an external FunASR service

Disable Compose management and override the endpoint:

```bash
VOXKEEP_MANAGE_FUNASR=0 \
VOXKEEP_ASR_EXTERNAL_HOST=192.0.2.10 \
VOXKEEP_ASR_EXTERNAL_PORT=10095 \
make run
```

For TLS or a non-root WebSocket path, supply the complete external-service configuration:

```bash
VOXKEEP_MANAGE_FUNASR=0 \
VOXKEEP_ASR_EXTERNAL_HOST=asr.example.com \
VOXKEEP_ASR_EXTERNAL_PORT=443 \
VOXKEEP_ASR_EXTERNAL_USE_SSL=1 \
VOXKEEP_ASR_EXTERNAL_PATH=/asr \
make run
```

`VOXKEEP_FUNASR_START_TIMEOUT_S` changes the endpoint wait limit. The Compose service also accepts
`VOXKEEP_FUNASR_IMAGE`, `VOXKEEP_FUNASR_CONTAINER`, and `VOXKEEP_FUNASR_DECODER_THREADS`.

## Inspect configuration and backend health

```bash
uv run --python 3.11 python -m voxkeep config validate --config config/config.yaml
uv run --python 3.11 python -m voxkeep backend doctor --config config/config.yaml
```

`backend doctor` performs a real WebSocket handshake against the configured endpoint and exits
non-zero when it is unhealthy.

`make doctor` always checks `config/config.yaml`. For another configuration file, use
`backend doctor --config <path>` for backend health and `config validate --config <path>` for
schema validation.

Configuration loads from `config/config.yaml`, with `VOXKEEP_*` environment variables overriding
individual values. YAML keys are strict: validation fails on unknown keys instead of silently
ignoring them. The most commonly useful overrides are:

- `VOXKEEP_MAX_QUEUE_SIZE` for the shared capacity of bounded runtime queues
- `VOXKEEP_ASR_EXTERNAL_HOST`, `VOXKEEP_ASR_EXTERNAL_PORT`,
  `VOXKEEP_ASR_EXTERNAL_PATH`, and `VOXKEEP_ASR_EXTERNAL_USE_SSL`
- `VOXKEEP_VAD_SPEECH_THRESHOLD` and `VOXKEEP_VAD_SILENCE_MS`
- `VOXKEEP_SQLITE_PATH`
- `VOXKEEP_INJECTOR_BACKEND` and `VOXKEEP_INJECTOR_AUTO_ENTER`
- `VOXKEEP_LOG_LEVEL`

Wake thresholds are configured per rule at `wake.rules[].threshold` in YAML. Removed YAML keys such
as `wake.threshold`, `storage.store_final_only`, and module-specific queue-size settings are
rejected. Their former environment-variable equivalents are not consumed. Use the top-level
`max_queue_size` or `VOXKEEP_MAX_QUEUE_SIZE` for queue capacity.

## Upgrading from the previous CLI

The single supported backend makes the old `backend list` and `backend current` commands
redundant; use `config validate` and `backend doctor` instead. The old `asset status` command and
its persisted backend-asset registry were also removed. Wake model assets now follow enabled
`wake.rules[]` entries and are prepared with `make setup-ai-models`.

## Troubleshooting

### `make doctor` reports no physical microphone

Run `pactl list short sources` and `pactl info`. Select a real input device instead of a
`.monitor` source, using `pavucontrol` or `pactl`.

### Wake/VAD imports or models are missing

```bash
make check-ai
```

`make check-ai` depends on model setup, which in turn synchronizes the runtime AI dependencies.

Wake models are derived from enabled `wake.rules[].keyword` entries in `config/config.yaml`. After
changing those rules, rerun `make setup-ai-models` so every enabled model is present.

### FunASR does not become ready

```bash
docker compose ps
make funasr-logs
uv run --python 3.11 python -m voxkeep backend doctor --config config/config.yaml
```

Confirm that host port `10096` is free, the container has enough CPU and memory, and model
downloads completed. Increase `VOXKEEP_FUNASR_START_TIMEOUT_S` for a slow first initialization.

### Text injection fails

Check `XDG_SESSION_TYPE`. The `auto` injector selects `xdotool` for X11 and `ydotool` for Wayland.
On Wayland, ensure `ydotoold` is running and the current user has the required device permissions.

### Runtime exits after a worker failure

An unexpectedly stopped worker is fatal by design. Inspect the first backend or worker error in
the log; later shutdown messages are usually consequences. Backend connection failures should
identify the configured endpoint and reconnect behavior explicitly.

## Data and shutdown

The default SQLite database is `data/asr.db`. The storage worker accepts final ASR events and
completed capture commands, normalizes them into its internal row model, and serializes all SQLite
writes. If `storage.jsonl_debug_path` is set, it mirrors those normalized rows to JSONL. Stop with
`Ctrl-C` or a normal termination signal so the runtime can stop and drain each pipeline stage in
producer-to-consumer order.
