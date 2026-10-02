# .env is optional; when present its RB_* settings override config.py defaults.
-include .env
export

UV := uv run

.PHONY: help install db-up db-down db-init db-reset verify lint typecheck test fmt doctor doctor-cpu fetch dates dates-debug inspect ingest search diff drift show regrade check-candidates questions power

help:  ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:  ## create .venv from uv.lock (exact versions, no resolution)
	uv sync --frozen

db-up:  ## start Postgres 17 + pgvector on localhost:5433 and wait until healthy
	docker compose up -d --wait db

db-down:  ## stop the database (data volume is kept)
	docker compose down

db-init:  ## create the schema if missing (idempotent)
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

# --- Ingestion (slice 2). Runs on a machine that can reach Riot's site. ---

fetch:  ## download Core Rules PDFs + patch notes into data/raw (SHA-1 verified)
	$(UV) python -m rb_errata.cli fetch

dates:  ## parse effective dates -> data/effective_dates.json (committed)
	$(UV) python -m rb_errata.cli dates

dates-debug:  ## show every date mention in the patch notes, in context (local only)
	$(UV) python -m rb_errata.cli dates --debug

inspect:  ## parse and chunk the PDFs; no database, no model, free
	$(UV) python -m rb_errata.cli inspect

ingest: fetch dates  ## everything: fetch, dates, chunk, embed, store -> data/corpus.json
	$(UV) python -m rb_errata.cli ingest

# Usage: make search Q="can a unit with deflect be targeted"
search:  ## naive vector search, NO date filter (slice 2 baseline)
	$(UV) python -m rb_errata.cli search "$(Q)"

# --- Temporal drift (slice 3) ---

# Usage: make diff OLD=1.3 NEW=1.4   (prints rule excerpts locally)
diff:  ## rules whose meaning changed between two versions
	$(UV) python -m rb_errata.cli diff $(or $(OLD),1.3) $(or $(NEW),1.4)

drift:  ## run evals/drift_candidates.yaml; writes evals/fixtures/*.json
	$(UV) python -m rb_errata.cli drift

# Usage: make regrade D=evals/fixtures/drift-2026-10-01
regrade:  ## re-grade stored fixtures against the current candidate labels (no model)
	$(UV) python -m rb_errata.cli regrade $(D)

check-candidates:  ## FULL text of each candidate rule in every version (local only)
	$(UV) python -m rb_errata.cli check-candidates

# Usage: make show F=evals/fixtures/drift-2026-10-01/deflect-chosen-twice.json
show:  ## re-display a fixture with rule text from the local database
	$(UV) python -m rb_errata.cli show $(F)

# --- Labelled question set (slice 4) ---

# Usage: make questions RULINGS=../riftboundfaq   (a clone of ChristianIvicevic/riftboundfaq;
# the commit is pinned in rb_errata/labels/rulings.py)
questions:  ## build evals/questions.yaml and check every expected ref against the corpus
	$(UV) python -m rb_errata.cli questions $(RULINGS)

power:  ## how many questions are needed (exact calculation, no model)
	$(UV) python -m rb_errata.cli power
