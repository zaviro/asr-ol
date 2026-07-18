# FunASR Runtime Baseline

Last verified: 2026-07-18.

## Deployment

- ASR backend id: `funasr_ws`.
- Container image: `registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.13`.
- Host endpoint: `ws://127.0.0.1:10096/`.
- Container listener: unencrypted WebSocket on port `10095`.
- Model persistence: Compose volume `funasr-models` mounted at `/workspace/models`.
- VoxKeep runs on the host; only FunASR runs in Docker.

Compose starts `funasr-wss-server-2pass` directly as the foreground container process. This
avoids relying on the image's interactive-shell workflow or on `run_server_2pass.sh`, which
backgrounds the server process.

## Client Protocol

The client behavior is based on FunASR's `runtime/docs/websocket_protocol_zh.md` and
`runtime/python/websocket/funasr_wss_client.py`:

1. Open a WebSocket with the `binary` subprotocol.
2. Send a JSON start message with `mode=2pass`, chunk/look-back settings, PCM format,
   sample rate, ITN setting, and `is_speaking=true`.
3. Send mono signed 16-bit PCM as binary messages.
4. Send `{"is_speaking": false}` when the stream closes.
5. Treat `2pass-online` messages as partial results and `2pass-offline` messages as corrected
   final results.

For `[5, 10, 5]` with `chunk_interval=10`, the official client sends 60 ms chunks. At 16 kHz
mono signed 16-bit PCM this is 960 samples, or 1920 bytes. VoxKeep therefore reframes its
32 ms internal audio frames before sending them to FunASR.

## Compatibility Boundary

Qwen/vLLM configuration, scripts, adapters, and tests are not part of the active runtime.
Runtime code and operator documentation must use this FunASR baseline; do not restore Qwen-specific
configuration or fallback paths.
