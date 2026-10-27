PYTHON ?= python3
export PYTHONPATH := src

.PHONY: run test check clean

run:
	$(PYTHON) src/cli_main.py

test:
	$(PYTHON) -m unittest discover -s tests -v

check:
	$(PYTHON) -m compileall -q src tests
	$(PYTHON) -m unittest discover -s tests

clean:
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type f \( -name '*.py[co]' -o -name '*.tmp' \) -delete
