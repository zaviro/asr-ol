from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "voxkeep"
LEGACY_PACKAGES = ("voxkeep.core", "voxkeep.infra", "voxkeep.services")


def _module_name_for(path: Path) -> str:
    return ".".join(path.relative_to(SRC_ROOT).with_suffix("").parts)


def _imported_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def _legacy_import_violations(package: str) -> list[str]:
    root = SRC_ROOT / package
    violations: list[str] = []
    for path in root.rglob("*.py"):
        module_name = _module_name_for(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _imported_names(tree):
            if any(
                imported == legacy or imported.startswith(f"{legacy}.")
                for legacy in LEGACY_PACKAGES
            ):
                violations.append(f"{module_name} -> {imported}")
    return sorted(violations)


def _legacy_runtime_files() -> list[str]:
    return [
        path.relative_to(SRC_ROOT).as_posix()
        for package in ("core", "infra", "services")
        for path in sorted((SRC_ROOT / package).rglob("*.py"))
    ]


def test_shared_does_not_import_legacy_layers() -> None:
    assert _legacy_import_violations("shared") == []


def test_bootstrap_does_not_import_legacy_layers() -> None:
    assert _legacy_import_violations("bootstrap") == []


def test_repository_has_no_legacy_runtime_files() -> None:
    assert _legacy_runtime_files() == []
