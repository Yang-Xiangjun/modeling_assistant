.PHONY: check lint fmt types test py310 schemas synthetic

PY310_RUN = uv run --python 3.10 --isolated --no-project --with pytest

check: lint types test py310

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

types:
	uv run mypy
	uv run mypy --config-file mypy-py310.ini

test:
	uv run pytest -q --cov --cov-report=term

# shared/ (and later nx_worker/) on a bare Python 3.10 with no project packages:
# proves 3.10 syntax and standard library only.
py310:
	$(PY310_RUN) python -m pytest tests/unit/shared -q -p no:cacheprovider

schemas:
	uv run python tools/export_schemas.py

synthetic:
	uv run python tools/make_synthetic.py
