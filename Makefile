.PHONY: sync sync-ai setup-ai-models run-ai check-ai doctor validate-config cli-check test test-fast test-unit test-architecture test-integration test-e2e test-cov typecheck run lint fmt fmt-check check shellcheck actionlint precommit

sync:
	uv sync --python 3.11 --group dev

sync-ai:
	uv sync --python 3.11 --group dev --group runtime-ai

setup-ai-models: sync-ai
	uv run --python 3.11 python scripts/setup_openwakeword_models.py

run-ai: setup-ai-models
	uv run --python 3.11 python -m voxkeep run --config config/config.yaml

check-ai: setup-ai-models
	uv run --python 3.11 python scripts/check_runtime_ai.py

doctor:
	uv run --python 3.11 python -m voxkeep doctor

validate-config:
	uv run --python 3.11 python -m voxkeep config validate --config config/config.yaml

cli-check:
	uv run --python 3.11 python -m voxkeep check

test:
	uv run --python 3.11 python -m pytest -q

test-fast:
	uv run --python 3.11 python -m pytest tests/unit tests/architecture -q

test-unit:
	uv run --python 3.11 python -m pytest tests/unit -q

test-architecture:
	uv run --python 3.11 python -m pytest tests/architecture -q

test-integration:
	uv run --python 3.11 python -m pytest tests/integration -q

test-e2e:
	uv run --python 3.11 python -m pytest tests/e2e -q

test-cov:
	uv run --python 3.11 python -m pytest --cov=src/voxkeep --cov-report=term --cov-report=xml

typecheck:
	uv run --python 3.11 pyright

run:
	uv run --python 3.11 python -m voxkeep run --config config/config.yaml

lint:
	uv run --python 3.11 ruff check src tests scripts

fmt:
	uv run --python 3.11 ruff format src tests scripts

fmt-check:
	uv run --python 3.11 ruff format --check src tests scripts

check: lint test

shellcheck:
	uv run --python 3.11 pre-commit run shellcheck --all-files

actionlint:
	uv run --python 3.11 pre-commit run actionlint --all-files

precommit:
	uv run --python 3.11 pre-commit run --all-files
