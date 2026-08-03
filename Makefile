PYTHON := .venv/bin/python
PYTEST := .venv/bin/pytest
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy

.PHONY: test lint format-check type-check memory-check quality

test:
	$(PYTEST) -m "not live_llm and not live_vision" -q

lint:
	$(RUFF) check .

format-check:
	$(RUFF) format --check .

type-check:
	$(MYPY) app scripts

memory-check:
	$(PYTHON) -m scripts.check_memory memory.md

quality: test lint format-check type-check memory-check

