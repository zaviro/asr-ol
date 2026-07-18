from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from importlib import import_module

import pytest

from voxkeep.shared.config import AppConfig, WakeRuleConfig, load_config


def test_load_config_from_yaml_and_env(tmp_path, monkeypatch):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "sample_rate: 16000\n"
        "channels: 1\n"
        "frame_ms: 20\n"
        "asr:\n"
        "  external:\n"
        "    host: 127.0.0.1\n"
        "    port: 10096\n"
        "wake:\n"
        "  rules:\n"
        "    - keyword: alexa\n"
        "      enabled: true\n"
        "      action: inject_text\n"
        "    - keyword: hey_jarvis\n"
        "      enabled: true\n"
        "      threshold: 0.6\n"
        "      action: openclaw_agent\n"
        "actions:\n"
        "  openclaw_agent:\n"
        '    command: ["openclaw", "agent", "--message", "{text}"]\n'
        "    timeout_s: 21\n"
        "capture:\n"
        "  pre_roll_ms: 500\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VOXKEEP_PRE_ROLL_MS", "1500")
    cfg = load_config(str(cfg_file))

    assert isinstance(cfg, AppConfig)
    assert cfg.audio_engine.sample_rate == 16000
    assert cfg.audio_engine.frame_ms == 20
    assert cfg.capture.pre_roll_ms == 1500
    assert cfg.asr.backend == "funasr_ws"
    assert cfg.asr.external_host == "127.0.0.1"
    assert cfg.asr.external_port == 10096
    assert cfg.asr.external_path == "/"
    assert cfg.asr.use_ssl is False
    assert cfg.asr.funasr_mode == "2pass"
    assert cfg.asr.funasr_chunk_size == (5, 10, 5)
    assert cfg.asr.funasr_itn is True
    assert [rule.keyword for rule in cfg.capture.enabled_wake_rules] == ["alexa", "hey_jarvis"]
    assert cfg.capture.enabled_wake_rules[1].threshold == 0.6
    assert cfg.capture.enabled_wake_rules[1].action == "openclaw_agent"
    assert cfg.injector.openclaw_command == ("openclaw", "agent", "--message", "{text}")
    assert cfg.injector.openclaw_timeout_s == 21.0


def test_load_config_applies_new_asr_env_overrides(tmp_path, monkeypatch) -> None:
    cfg_file = tmp_path / "env.yaml"
    cfg_file.write_text("{}\n", encoding="utf-8")

    monkeypatch.setenv("VOXKEEP_ASR_BACKEND", "funasr_ws")
    monkeypatch.setenv("VOXKEEP_ASR_EXTERNAL_HOST", "10.0.0.7")
    monkeypatch.setenv("VOXKEEP_ASR_EXTERNAL_PORT", "11096")

    cfg = load_config(cfg_file)

    assert cfg.asr.backend == "funasr_ws"
    assert cfg.asr.external_host == "10.0.0.7"
    assert cfg.asr.external_port == 11096


def test_load_config_supports_funasr_backend_and_runtime_reconnect_settings(tmp_path) -> None:
    cfg_file = tmp_path / "funasr.yaml"
    cfg_file.write_text(
        "asr:\n"
        "  backend: funasr_ws\n"
        "  external:\n"
        "    host: 127.0.0.1\n"
        "    port: 10096\n"
        "    path: /\n"
        "    use_ssl: false\n"
        "  runtime:\n"
        "    reconnect_initial_s: 2.5\n"
        "    reconnect_max_s: 9.0\n",
        encoding="utf-8",
    )

    cfg = load_config(cfg_file)

    assert cfg.asr.backend == "funasr_ws"
    assert cfg.asr.external_port == 10096
    assert cfg.asr.external_path == "/"
    assert cfg.asr.reconnect_initial_s == 2.5
    assert cfg.asr.reconnect_max_s == 9.0


def test_load_config_normalizes_supported_backend_id(tmp_path) -> None:
    cfg_file = tmp_path / "backend.yaml"
    cfg_file.write_text("asr:\n  backend: ' FUNASR_WS '\n", encoding="utf-8")

    assert load_config(cfg_file).asr.backend == "funasr_ws"


def test_load_config_rejects_unsupported_backend(tmp_path) -> None:
    cfg_file = tmp_path / "backend.yaml"
    cfg_file.write_text("asr:\n  backend: qwen\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported asr backend: qwen"):
        load_config(cfg_file)


def test_load_config_supports_funasr_protocol_settings(tmp_path) -> None:
    cfg_file = tmp_path / "funasr-options.yaml"
    cfg_file.write_text(
        "asr:\n"
        "  backend: funasr_ws\n"
        "  funasr:\n"
        "    mode: 2pass\n"
        "    chunk_size: [0, 10, 5]\n"
        "    chunk_interval: 10\n"
        "    encoder_chunk_look_back: 4\n"
        "    decoder_chunk_look_back: 1\n"
        "    itn: false\n",
        encoding="utf-8",
    )

    cfg = load_config(cfg_file)

    assert cfg.asr.funasr_mode == "2pass"
    assert cfg.asr.funasr_chunk_size == (0, 10, 5)
    assert cfg.asr.funasr_chunk_interval == 10
    assert cfg.asr.funasr_encoder_chunk_look_back == 4
    assert cfg.asr.funasr_decoder_chunk_look_back == 1
    assert cfg.asr.funasr_itn is False


def test_load_config_applies_runtime_reconnect_env_overrides(tmp_path, monkeypatch) -> None:
    cfg_file = tmp_path / "reconnect-env.yaml"
    cfg_file.write_text(
        "asr:\n  runtime:\n    reconnect_initial_s: 2.5\n    reconnect_max_s: 9.0\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("VOXKEEP_ASR_RUNTIME_RECONNECT_INITIAL_S", "3.25")
    monkeypatch.setenv("VOXKEEP_ASR_RUNTIME_RECONNECT_MAX_S", "11.5")

    cfg = load_config(cfg_file)

    assert cfg.asr.reconnect_initial_s == 3.25
    assert cfg.asr.reconnect_max_s == 11.5


def test_app_config_is_frozen(app_config: AppConfig):
    with pytest.raises(FrozenInstanceError):
        app_config.log_level = "DEBUG"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        app_config.audio_engine.sample_rate = 8000  # type: ignore[misc]


@pytest.mark.parametrize(
    ("sub_config", "overrides", "match_text"),
    [
        ("audio_engine", {"sample_rate": 0}, "audio_engine.sample_rate"),
        ("audio_engine", {"max_queue_size": 0}, "audio_engine.max_queue_size"),
        ("capture", {"vad_speech_threshold": 1.5}, "capture.vad_speech_threshold"),
        ("asr", {"reconnect_max_s": 0.5}, "asr.reconnect_max_s"),
        ("asr", {"external_path": "not-slash"}, "asr.external_path"),
        ("asr", {"funasr_chunk_size": (5, 0, 5)}, r"asr.funasr.chunk_size\[1\]"),
    ],
)
def test_app_config_validation_rejects_invalid_values(
    app_config: AppConfig,
    sub_config: str,
    overrides: dict[str, object],
    match_text: str,
):
    target = getattr(app_config, sub_config)
    new_sub = replace(target, **overrides)
    with pytest.raises(ValueError, match=match_text):
        replace(app_config, **{sub_config: new_sub})


def test_app_config_rejects_duplicate_wake_keywords(app_config: AppConfig) -> None:
    new_capture = replace(
        app_config.capture,
        wake_rules=(
            WakeRuleConfig("alexa", True, 0.5, "inject_text"),
            WakeRuleConfig("alexa", True, 0.6, "openclaw_agent"),
        ),
    )
    with pytest.raises(ValueError, match="duplicate keyword"):
        replace(app_config, capture=new_capture)


def test_app_config_rejects_empty_wake_keyword(app_config: AppConfig) -> None:
    new_capture = replace(
        app_config.capture,
        wake_rules=(WakeRuleConfig("", True, 0.5, "inject_text"),),
    )
    with pytest.raises(ValueError, match="empty keyword"):
        replace(app_config, capture=new_capture)


def test_app_config_rejects_empty_wake_action(app_config: AppConfig) -> None:
    new_capture = replace(
        app_config.capture,
        wake_rules=(WakeRuleConfig("alexa", True, 0.5, " "),),
    )
    with pytest.raises(ValueError, match="action must not be empty"):
        replace(app_config, capture=new_capture)


def test_load_config_raises_when_file_missing(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="config file not found"):
        load_config(tmp_path / "missing.yaml")


def test_load_config_raises_when_yaml_root_is_not_mapping(tmp_path) -> None:
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("- not-a-mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="config root must be a mapping"):
        load_config(cfg_file)


def test_load_config_raises_when_wake_rule_item_is_not_mapping(tmp_path) -> None:
    cfg_file = tmp_path / "bad_rules.yaml"
    cfg_file.write_text("wake:\n  rules:\n    - alexa\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"config key must be a mapping: wake\.rules\[0\]"):
        load_config(cfg_file)


@pytest.mark.parametrize(
    ("yaml_text", "unknown_key"),
    [
        ("unexpected: true\n", "unexpected"),
        ("asr:\n  external:\n    hostname: localhost\n", "asr.external.hostname"),
        ("wake:\n  threshold: 0.4\n", "wake.threshold"),
        ("storage:\n  store_final_only: true\n", "storage.store_final_only"),
        (
            "wake:\n  rules:\n    - keyword: alexa\n      threshhold: 0.4\n",
            "wake.rules[0].threshhold",
        ),
    ],
)
def test_load_config_rejects_unknown_yaml_keys(
    tmp_path,
    yaml_text: str,
    unknown_key: str,
) -> None:
    cfg_file = tmp_path / "unknown.yaml"
    cfg_file.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        load_config(cfg_file)
    assert str(exc_info.value) == f"unknown config key: {unknown_key}"


@pytest.mark.parametrize(
    ("yaml_text", "message"),
    [
        ("wake: false\n", "config key must be a mapping: wake"),
        ("wake:\n  rules: false\n", "config key must be a list: wake.rules"),
    ],
)
def test_load_config_reports_invalid_container_types(
    tmp_path,
    yaml_text: str,
    message: str,
) -> None:
    cfg_file = tmp_path / "invalid-shape.yaml"
    cfg_file.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_config(cfg_file)


@pytest.mark.parametrize(
    ("env_name", "value"),
    [
        ("VOXKEEP_ASR_EXTERNAL_PORT", "not-a-port"),
        ("VOXKEEP_INJECTOR_AUTO_ENTER", "maybe"),
    ],
)
def test_load_config_reports_invalid_environment_values(
    tmp_path,
    monkeypatch,
    env_name: str,
    value: str,
) -> None:
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv(env_name, value)

    with pytest.raises(ValueError, match=f"invalid value for {env_name}"):
        load_config(cfg_file)


def test_enabled_wake_rules_filters_disabled_rules(app_config: AppConfig) -> None:
    new_capture = replace(
        app_config.capture,
        wake_rules=(
            WakeRuleConfig("alexa", True, 0.5, "inject_text"),
            WakeRuleConfig("hey_jarvis", False, 0.6, "openclaw_agent"),
        ),
    )
    cfg = replace(app_config, capture=new_capture)

    assert cfg.capture.enabled_wake_rules == (WakeRuleConfig("alexa", True, 0.5, "inject_text"),)


def test_frame_samples_property_is_derived_correctly(app_config: AppConfig) -> None:
    new_ae = replace(app_config.audio_engine, sample_rate=16000, frame_ms=32)
    cfg = replace(app_config, audio_engine=new_ae)

    assert cfg.audio_engine.frame_samples == 512


def test_asr_ws_url_uses_ws_or_wss_based_on_ssl(app_config: AppConfig) -> None:
    new_asr_ws = replace(app_config.asr, use_ssl=False)
    assert replace(app_config, asr=new_asr_ws).asr.ws_url.startswith("ws://")

    new_asr_wss = replace(app_config.asr, use_ssl=True)
    assert replace(app_config, asr=new_asr_wss).asr.ws_url.startswith("wss://")


def test_config_split_modules_reexport_public_api() -> None:
    schema = import_module("voxkeep.shared.config_schema")
    loader = import_module("voxkeep.shared.config_loader")

    assert schema.AppConfig is AppConfig
    assert schema.WakeRuleConfig is WakeRuleConfig
    assert loader.load_config is load_config
