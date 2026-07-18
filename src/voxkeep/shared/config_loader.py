"""Configuration loading and merge helpers."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
from typing import Any, cast

import yaml

from voxkeep.shared.config_schema import (
    AppConfig,
    AsrConfig,
    AudioEngineConfig,
    CaptureConfig,
    InjectorConfig,
    StorageConfig,
    WakeRuleConfig,
)


def _parse_bool(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean: {raw}")


_ENV_MAP = {
    "VOXKEEP_SAMPLE_RATE": ("sample_rate", int),
    "VOXKEEP_CHANNELS": ("channels", int),
    "VOXKEEP_FRAME_MS": ("frame_ms", int),
    "VOXKEEP_MAX_QUEUE_SIZE": ("max_queue_size", int),
    "VOXKEEP_ASR_BACKEND": ("asr.backend", str),
    "VOXKEEP_ASR_EXTERNAL_HOST": ("asr.external.host", str),
    "VOXKEEP_ASR_EXTERNAL_PORT": ("asr.external.port", int),
    "VOXKEEP_ASR_EXTERNAL_PATH": ("asr.external.path", str),
    "VOXKEEP_ASR_EXTERNAL_USE_SSL": ("asr.external.use_ssl", _parse_bool),
    "VOXKEEP_ASR_RUNTIME_RECONNECT_INITIAL_S": ("asr.runtime.reconnect_initial_s", float),
    "VOXKEEP_ASR_RUNTIME_RECONNECT_MAX_S": ("asr.runtime.reconnect_max_s", float),
    "VOXKEEP_ASR_FUNASR_MODE": ("asr.funasr.mode", str),
    "VOXKEEP_ASR_FUNASR_CHUNK_INTERVAL": ("asr.funasr.chunk_interval", int),
    "VOXKEEP_ASR_FUNASR_ENCODER_LOOK_BACK": ("asr.funasr.encoder_chunk_look_back", int),
    "VOXKEEP_ASR_FUNASR_DECODER_LOOK_BACK": ("asr.funasr.decoder_chunk_look_back", int),
    "VOXKEEP_ASR_FUNASR_ITN": ("asr.funasr.itn", _parse_bool),
    "VOXKEEP_VAD_SPEECH_THRESHOLD": ("vad.speech_threshold", float),
    "VOXKEEP_VAD_SILENCE_MS": ("vad.silence_ms", int),
    "VOXKEEP_PRE_ROLL_MS": ("capture.pre_roll_ms", int),
    "VOXKEEP_CAPTURE_ARMED_TIMEOUT_MS": ("capture.armed_timeout_ms", int),
    "VOXKEEP_SQLITE_PATH": ("storage.sqlite_path", str),
    "VOXKEEP_JSONL_DEBUG_PATH": ("storage.jsonl_debug_path", str),
    "VOXKEEP_INJECTOR_BACKEND": ("injector.backend", str),
    "VOXKEEP_INJECTOR_AUTO_ENTER": ("injector.auto_enter", _parse_bool),
    "VOXKEEP_XDOTOOL_DELAY_MS": ("injector.xdotool_delay_ms", int),
    "VOXKEEP_OPENCLAW_TIMEOUT_S": ("actions.openclaw_agent.timeout_s", float),
    "VOXKEEP_LOG_LEVEL": ("runtime.log_level", str),
}

_DEFAULTS: dict[str, Any] = {
    "sample_rate": 16000,
    "channels": 1,
    "frame_ms": 32,
    "max_queue_size": 512,
    "asr": {
        "backend": "funasr_ws",
        "external": {"host": "127.0.0.1", "port": 10096, "path": "/", "use_ssl": False},
        "runtime": {"reconnect_initial_s": 1.0, "reconnect_max_s": 30.0},
        "funasr": {
            "mode": "2pass",
            "chunk_size": [5, 10, 5],
            "chunk_interval": 10,
            "encoder_chunk_look_back": 4,
            "decoder_chunk_look_back": 1,
            "itn": True,
        },
    },
    "wake": {
        "rules": [
            {"keyword": "alexa", "enabled": True, "threshold": 0.5, "action": "inject_text"},
            {
                "keyword": "hey_jarvis",
                "enabled": True,
                "threshold": 0.5,
                "action": "openclaw_agent",
            },
            {
                "keyword": "hey_mycroft",
                "enabled": False,
                "threshold": 0.5,
                "action": "inject_text",
            },
            {
                "keyword": "hey_rhasspy",
                "enabled": False,
                "threshold": 0.5,
                "action": "inject_text",
            },
            {"keyword": "timer", "enabled": False, "threshold": 0.5, "action": "inject_text"},
            {
                "keyword": "weather",
                "enabled": False,
                "threshold": 0.5,
                "action": "inject_text",
            },
        ]
    },
    "vad": {"speech_threshold": 0.5, "silence_ms": 800},
    "capture": {"pre_roll_ms": 600, "armed_timeout_ms": 5000},
    "storage": {"sqlite_path": "data/asr.db", "jsonl_debug_path": ""},
    "injector": {"backend": "auto", "auto_enter": False, "xdotool_delay_ms": 1},
    "actions": {
        "openclaw_agent": {
            "command": ["openclaw", "agent", "--message", "{text}"],
            "timeout_s": 20.0,
        }
    },
    "runtime": {"log_level": "INFO"},
}


def _validate_known_keys(value: Any, template: Any, path: str = "") -> None:
    """Reject YAML keys that are absent from the default configuration shape."""
    if isinstance(template, dict):
        if not isinstance(value, dict):
            raise ValueError(f"config key must be a mapping: {path}")
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key not in template:
                raise ValueError(f"unknown config key: {child_path}")
            _validate_known_keys(child, template[key], child_path)
    elif isinstance(template, list):
        if not isinstance(value, list):
            raise ValueError(f"config key must be a list: {path}")
        if not template:
            return
        for index, child in enumerate(value):
            _validate_known_keys(child, template[0], f"{path}[{index}]")


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _set_nested(conf: dict[str, Any], dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    cur = conf
    for key in keys[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[keys[-1]] = value


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping")
    return data


def _apply_env(conf: dict[str, Any]) -> dict[str, Any]:
    for env_name, (dotted, caster) in _ENV_MAP.items():
        raw = os.environ.get(env_name)
        if raw is None:
            continue
        try:
            value = caster(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid value for {env_name}: {raw!r}") from exc
        _set_nested(conf, dotted, value)
    return conf


def _parse_wake_rules(data: list[dict[str, Any]]) -> tuple[WakeRuleConfig, ...]:
    rules: list[WakeRuleConfig] = []
    for item in data:
        rules.append(
            WakeRuleConfig(
                keyword=str(item.get("keyword", "")).strip(),
                enabled=bool(item.get("enabled", True)),
                threshold=float(item.get("threshold", 0.5)),
                action=str(item.get("action", "inject_text")).strip() or "inject_text",
            )
        )
    return tuple(rules)


def load_config(path: str | Path) -> AppConfig:
    """Load config from YAML file and environment variables."""
    user_conf = _load_yaml(Path(path))
    _validate_known_keys(user_conf, _DEFAULTS)
    merged = deepcopy(_DEFAULTS)
    merged = _deep_merge(merged, user_conf)
    merged = _apply_env(merged)

    wake = merged.get("wake", {})
    vad = merged.get("vad", {})
    capture = merged.get("capture", {})
    storage = merged.get("storage", {})
    injector = merged.get("injector", {})
    actions = merged.get("actions", {})
    runtime = merged.get("runtime", {})
    asr = merged.get("asr", {})
    external = asr.get("external", {})
    asr_runtime = asr.get("runtime", {})
    funasr = asr.get("funasr", {})

    openclaw = actions.get("openclaw_agent", {})
    command = tuple(str(part) for part in openclaw.get("command", []))

    reconnect_initial_s = float(asr_runtime.get("reconnect_initial_s", 1.0))
    reconnect_max_s = float(asr_runtime.get("reconnect_max_s", 30.0))

    # Build nested configs
    audio_engine_cfg = AudioEngineConfig(
        sample_rate=int(merged["sample_rate"]),
        channels=int(merged["channels"]),
        frame_ms=int(merged["frame_ms"]),
        max_queue_size=int(merged["max_queue_size"]),
    )

    asr_cfg = AsrConfig(
        backend=str(asr["backend"]).strip().lower(),
        external_host=str(external["host"]),
        external_port=int(external["port"]),
        external_path=str(external["path"]),
        use_ssl=bool(external["use_ssl"]),
        reconnect_initial_s=reconnect_initial_s,
        reconnect_max_s=reconnect_max_s,
        funasr_mode=str(funasr["mode"]),
        funasr_chunk_size=cast(
            tuple[int, int, int],
            tuple(int(value) for value in funasr["chunk_size"]),
        ),
        funasr_chunk_interval=int(funasr["chunk_interval"]),
        funasr_encoder_chunk_look_back=int(funasr["encoder_chunk_look_back"]),
        funasr_decoder_chunk_look_back=int(funasr["decoder_chunk_look_back"]),
        funasr_itn=bool(funasr["itn"]),
        max_queue_size=int(merged["max_queue_size"]),
        sample_rate=int(merged["sample_rate"]),
    )

    capture_cfg = CaptureConfig(
        wake_rules=_parse_wake_rules(list(wake.get("rules", []))),
        vad_speech_threshold=float(vad["speech_threshold"]),
        vad_silence_ms=int(vad["silence_ms"]),
        pre_roll_ms=int(capture["pre_roll_ms"]),
        armed_timeout_ms=int(capture["armed_timeout_ms"]),
    )

    storage_cfg = StorageConfig(
        sqlite_path=str(storage["sqlite_path"]),
        jsonl_debug_path=str(storage.get("jsonl_debug_path") or "") or None,
    )

    injector_cfg = InjectorConfig(
        backend=str(injector["backend"]),
        auto_enter=bool(injector["auto_enter"]),
        xdotool_delay_ms=int(injector["xdotool_delay_ms"]),
        openclaw_command=command,
        openclaw_timeout_s=float(openclaw["timeout_s"]),
    )

    return AppConfig(
        audio_engine=audio_engine_cfg,
        asr=asr_cfg,
        capture=capture_cfg,
        storage=storage_cfg,
        injector=injector_cfg,
        log_level=str(runtime["log_level"]),
    )


__all__ = ["load_config"]
