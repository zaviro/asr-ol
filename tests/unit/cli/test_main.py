from __future__ import annotations

from pathlib import Path
import subprocess
import types

from voxkeep.cli import main as cli_main


class _Parser:
    def parse_args(self, _argv=None):  # type: ignore[no-untyped-def]
        return types.SimpleNamespace(config="config/config.yaml", func=cli_main._cmd_run)


class _RuntimeBase:
    def __init__(self, _cfg) -> None:  # type: ignore[no-untyped-def]
        self.stop_event = types.SimpleNamespace()
        self.started = False
        self.stopped = False
        self._fatal_error: str | None = None

    @property
    def fatal_error(self) -> str | None:
        return self._fatal_error

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class _RuntimeHealthy(_RuntimeBase):
    def run_forever(self) -> None:
        return


class _RuntimeFatal(_RuntimeBase):
    def run_forever(self) -> None:
        self._fatal_error = "worker stopped unexpectedly: asr_worker"


class _RuntimeKeyboard(_RuntimeBase):
    def run_forever(self) -> None:
        raise KeyboardInterrupt


def _setup_common(monkeypatch, runtime_cls: type[_RuntimeBase]) -> None:
    monkeypatch.setattr(cli_main, "build_arg_parser", lambda: _Parser())
    monkeypatch.setattr(
        cli_main, "load_config", lambda _path: types.SimpleNamespace(log_level="INFO")
    )
    monkeypatch.setattr(cli_main, "configure_logging", lambda _level: None)
    monkeypatch.setattr(cli_main, "install_signal_handlers", lambda _stop_event: None)
    monkeypatch.setattr(cli_main, "build_runtime", runtime_cls)


def test_main_returns_zero_on_healthy_exit(monkeypatch):
    _setup_common(monkeypatch, _RuntimeHealthy)

    code = cli_main.main()

    assert code == cli_main.EXIT_OK


def test_main_returns_nonzero_on_runtime_fatal(monkeypatch):
    _setup_common(monkeypatch, _RuntimeFatal)

    code = cli_main.main()

    assert code == cli_main.EXIT_RUNTIME_FAILURE


def test_main_returns_zero_on_keyboard_interrupt(monkeypatch):
    _setup_common(monkeypatch, _RuntimeKeyboard)

    code = cli_main.main()

    assert code == cli_main.EXIT_OK


def test_cli_uses_bootstrap_runtime_builder() -> None:
    assert cli_main.build_runtime.__module__ == "voxkeep.bootstrap.runtime_app"


def test_normalize_cli_argv_defaults_to_run_for_legacy_options() -> None:
    assert cli_main.normalize_cli_argv(["--config", "custom.yaml"]) == [
        "run",
        "--config",
        "custom.yaml",
    ]


def test_normalize_cli_argv_leaves_help_at_root() -> None:
    assert cli_main.normalize_cli_argv(["--help"]) == ["--help"]


def test_normalize_cli_argv_does_not_rewrite_known_subcommands() -> None:
    assert cli_main.normalize_cli_argv(["backend", "doctor"]) == ["backend", "doctor"]


def test_main_dispatches_config_validate(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "load_config", lambda _path: types.SimpleNamespace())

    code = cli_main.main(["config", "validate", "--config", "config/config.yaml"])

    assert code == cli_main.EXIT_OK


def test_main_returns_nonzero_when_config_validate_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_main, "load_config", lambda _path: (_ for _ in ()).throw(ValueError("bad"))
    )

    code = cli_main.main(["config", "validate", "--config", "config/config.yaml"])

    assert code == cli_main.EXIT_COMMAND_FAILURE


def test_main_runs_doctor_script(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool, cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert check is False
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli_main, "_project_root", lambda: Path("/repo"))
    monkeypatch.setattr(cli_main, "_repo_path", lambda *_parts: Path("/repo/scripts/check_env.sh"))
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    code = cli_main.main(["doctor"])

    assert code == cli_main.EXIT_OK
    assert calls == [["/repo/scripts/check_env.sh"]]


def test_main_runs_check_commands_in_order(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_dev_command(*args: str) -> list[str]:
        return list(args)

    def fake_run(cmd: list[str], check: bool, cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert check is False
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli_main, "_project_root", lambda: Path("/repo"))
    monkeypatch.setattr(cli_main, "_dev_command", fake_dev_command)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    code = cli_main.main(["check"])

    assert code == cli_main.EXIT_OK
    assert calls == [
        ["ruff", "check", "src", "tests", "scripts"],
        ["pyright"],
        ["pytest", "-q"],
    ]


def test_dev_command_wraps_python_tools_when_uv_is_available(monkeypatch) -> None:
    monkeypatch.setattr(
        cli_main.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None
    )

    command = cli_main._dev_command("pytest", "-q")

    assert command == ["/usr/bin/uv", "run", "--python", "3.11", "python", "-m", "pytest", "-q"]


def test_build_arg_parser_registers_backend_doctor() -> None:
    parser = cli_main.build_arg_parser()

    backend_doctor_args = parser.parse_args(["backend", "doctor"])

    assert backend_doctor_args.func is cli_main._cmd_backend_doctor


def test_backend_doctor_command_reports_backend_health(monkeypatch, capsys) -> None:
    cfg = types.SimpleNamespace(
        asr=types.SimpleNamespace(
            backend="funasr_ws",
            ws_url="ws://127.0.0.1:10096/",
        )
    )
    monkeypatch.setattr(cli_main, "load_config", lambda _path: cfg)
    monkeypatch.setattr(
        cli_main,
        "probe_websocket_handshake",
        lambda _url: (True, True, "websocket handshake ok: ws://127.0.0.1:10096/"),
    )
    monkeypatch.setattr(
        cli_main,
        "classify_backend_health",
        lambda **kwargs: types.SimpleNamespace(
            state="healthy",
            reason="ok",
            detail=kwargs["detail"],
        ),
    )

    code = cli_main._cmd_backend_doctor(types.SimpleNamespace(config="config/config.yaml"))
    captured = capsys.readouterr()

    assert code == cli_main.EXIT_OK
    assert captured.out.splitlines() == [
        "backend_id=funasr_ws",
        "state=healthy",
        "reason=ok",
        "detail=websocket handshake ok: ws://127.0.0.1:10096/",
    ]


def test_backend_doctor_command_returns_nonzero_for_unhealthy_backend(monkeypatch, capsys) -> None:
    cfg = types.SimpleNamespace(
        asr=types.SimpleNamespace(
            backend="funasr_ws",
            ws_url="ws://127.0.0.1:10096/",
        )
    )
    monkeypatch.setattr(cli_main, "load_config", lambda _path: cfg)
    monkeypatch.setattr(
        cli_main,
        "probe_websocket_handshake",
        lambda _url: (True, False, "handshake failed"),
    )
    monkeypatch.setattr(
        cli_main,
        "classify_backend_health",
        lambda **kwargs: types.SimpleNamespace(
            state="degraded",
            reason="handshake_failed",
            detail=kwargs["detail"],
        ),
    )

    code = cli_main._cmd_backend_doctor(types.SimpleNamespace(config="config/config.yaml"))
    captured = capsys.readouterr()

    assert code == cli_main.EXIT_COMMAND_FAILURE
    assert captured.out.splitlines() == [
        "backend_id=funasr_ws",
        "state=degraded",
        "reason=handshake_failed",
        "detail=handshake failed",
    ]
