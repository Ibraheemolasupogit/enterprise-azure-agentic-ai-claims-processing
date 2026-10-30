PYTHON ?= .venv/bin/python

.PHONY: test lint format format-check typecheck check package

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

package:
	$(PYTHON) -m pip wheel --no-index --no-cache-dir --no-deps --no-build-isolation --wheel-dir dist .
	$(PYTHON) -c 'from setuptools.build_meta import build_sdist; build_sdist("dist")'
