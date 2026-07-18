from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "voxkeep"
MICROPHONE_OWNER = Path("modules/audio_engine/infrastructure/audio_capture.py")
STORAGE_ROOT = Path("modules/storage")

_MICROPHONE_OPEN_CALLS = {
    "alsaaudio.PCM",
    "pyaudio.PyAudio().open",
    "soundcard.all_microphones",
    "soundcard.default_microphone",
    "soundcard.get_microphone",
    "sounddevice.InputStream",
    "sounddevice.RawInputStream",
    "sounddevice.RawStream",
    "sounddevice.Stream",
    "sounddevice.playrec",
    "sounddevice.rec",
}
_SQLITE_CONNECT_CALLS = {"sqlite3.connect", "sqlite3.dbapi2.connect"}


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                bound_name = imported.asname or imported.name.split(".", 1)[0]
                aliases[bound_name] = imported.name if imported.asname else bound_name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for imported in node.names:
                if imported.name == "*":
                    continue
                bound_name = imported.asname or imported.name
                aliases[bound_name] = f"{node.module}.{imported.name}"
    return aliases


def _qualified_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        owner = _qualified_name(node.value, aliases)
        return f"{owner}.{node.attr}" if owner else None
    if isinstance(node, ast.Call):
        callee = _qualified_name(node.func, aliases)
        return f"{callee}()" if callee else None
    return None


def _local_aliases(tree: ast.AST, aliases: dict[str, str]) -> dict[str, str]:
    """Resolve simple assignments such as ``audio = pyaudio.PyAudio()``."""
    resolved = dict(aliases)
    for node in ast.walk(tree):
        target: ast.AST | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if not isinstance(target, ast.Name) or value is None:
            continue
        qualified = _qualified_name(value, resolved)
        if qualified is not None:
            resolved[target.id] = qualified
    return resolved


def _calls_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases = _local_aliases(tree, _import_aliases(tree))
    return [
        qualified
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (qualified := _qualified_name(node.func, aliases)) is not None
    ]


def _find_calls(call_names: set[str]) -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        relative_path = path.relative_to(SRC_ROOT)
        matches.extend((relative_path, call) for call in _calls_in(path) if call in call_names)
    return matches


def test_only_audio_capture_opens_microphone_devices() -> None:
    calls = _find_calls(_MICROPHONE_OPEN_CALLS)

    assert calls, "architecture scan did not find the repository's microphone opening call"
    assert [(str(path), call) for path, call in calls if path != MICROPHONE_OWNER] == []


def test_only_storage_module_opens_sqlite_connections() -> None:
    calls = _find_calls(_SQLITE_CONNECT_CALLS)

    assert calls, "architecture scan did not find the repository's SQLite connection call"
    assert [
        (str(path), call) for path, call in calls if not path.is_relative_to(STORAGE_ROOT)
    ] == []
