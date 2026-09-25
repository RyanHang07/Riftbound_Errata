# .env is optional; when present its RB_* settings override config.py defaults.
-include .env
export

UV := uv run

.PHONY: help install db-up db-down db-init verify lint typecheck test fmt doctor doctor-cpu

help:  ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:  ## create .venv from uv.lock (exact versions, no resolution)
	uv sync --frozen

db-up:  ## start Postgres 17 + pgvector on localhost:5433 and wait until healthy
	docker compose up -d --wait db

db-down:  ## stop the database (data volume is kept)
	docker compose down

db-init:  ## ensure the pgvector extension exists (idempotent)
	$(UV) python -m rb_errata.cli init-db

# The free layer. No database, no model, seconds. Runs after every change.
verify: lint typecheck test  ## lint + typecheck + contract tests

lint:
	$(UV) ruff check .
	$(UV) ruff format --check .

typecheck:
	$(UV) mypy

test:
	$(UV) pytest

fmt:  ## apply formatting and safe lint fixes
	$(UV) ruff format .
	$(UV) ruff check --fix .

# The next layer up: real database, real models, no corpus.
doctor:  ## can the pipeline run at all? no corpus needed
	$(UV) python -m rb_errata.cli doctor

# Same checks with both models kept off the GPU. Use this for any number that
# goes into a budget or the writeup: the target machine has no GPU.
doctor-cpu:  ## doctor on CPU only (target-hardware numbers)
	RB_CPU_ONLY=true $(UV) python -m rb_errata.cli doctor
