from __future__ import annotations

from dataclasses import replace

import pytest

from voxkeep.shared.config import AppConfig
from voxkeep.modules.injection.infrastructure.factory import build_injector
from voxkeep.modules.injection.infrastructure.xdotool_injector import XdotoolInjector
from voxkeep.modules.injection.infrastructure.ydotool_injector import YdotoolInjector


@pytest.mark.parametrize(
    ("session_type", "backend", "expected_type"),
    [
        ("x11", "auto", XdotoolInjector),
        ("wayland", "auto", YdotoolInjector),
        ("x11", "ydotool", YdotoolInjector),
    ],
)
def test_factory_selects_backend(
    monkeypatch,
    app_config: AppConfig,
    session_type: str,
    backend: str,
    expected_type: type,
):
    monkeypatch.setenv("XDG_SESSION_TYPE", session_type)
    cfg = replace(app_config.injector, backend=backend)

    injector = build_injector(cfg)

    assert isinstance(injector, expected_type)


def test_factory_auto_selects_xdotool_when_xdg_not_set(monkeypatch, app_config: AppConfig):
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    cfg = replace(app_config.injector, backend="auto")

    injector = build_injector(cfg)

    assert isinstance(injector, XdotoolInjector)


def test_factory_auto_selects_ydotool_for_wayland(monkeypatch, app_config: AppConfig):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    cfg = replace(app_config.injector, backend="auto")

    injector = build_injector(cfg)

    assert isinstance(injector, YdotoolInjector)


def test_factory_auto_selects_xdotool_for_x11(monkeypatch, app_config: AppConfig):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    cfg = replace(app_config.injector, backend="auto")

    injector = build_injector(cfg)

    assert isinstance(injector, XdotoolInjector)


def test_factory_explicit_xdotool_backend(monkeypatch, app_config: AppConfig):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    cfg = replace(app_config.injector, backend="xdotool")

    injector = build_injector(cfg)

    assert isinstance(injector, XdotoolInjector)


def test_factory_preserves_injector_config_options(app_config: AppConfig):
    cfg = replace(app_config.injector, backend="xdotool", xdotool_delay_ms=5, auto_enter=True)

    injector = build_injector(cfg)

    assert isinstance(injector, XdotoolInjector)
    assert injector._delay_ms == 5
    assert injector._auto_enter is True
