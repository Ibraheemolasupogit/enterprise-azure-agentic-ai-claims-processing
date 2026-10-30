PYTHON ?= .venv/bin/python

.PHONY: test lint format format-check typecheck check package dataset-check benchmark-check

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

format:
	$(PYTHON) -m ruff format src tests

format-check:
	$(PYTHON) -m ruff format --check src tests

typecheck:
	$(PYTHON) -m mypy

check: format-check lint typecheck test

dataset-check:
	PYTHONPATH=src $(PYTHON) -m claims_ai.dataset check --root data/synthetic/motor/v1

benchmark-check:
	$(PYTHON) -m pytest tests/test_benchmark_scoring.py tests/test_benchmark_runner.py

package:
	$(PYTHON) -m pip wheel --no-index --no-cache-dir --no-deps --no-build-isolation --wheel-dir dist .
	$(PYTHON) -c 'from setuptools.build_meta import build_sdist; build_sdist("dist")'
