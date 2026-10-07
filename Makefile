# .env is optional; when present its RB_* settings override config.py defaults.
-include .env
export

# Embedder profile (rb_errata/config.py EMBED_PROFILES): `make recall EMBED=nomic`.
# Unset means the default, qwen3 (A30). Works with every target that embeds or reads
# vectors: doctor, ingest, search, recall.
ifdef EMBED
export RB_EMBED_PROFILE := $(EMBED)
endif

UV := uv run

.PHONY: help install db-up db-down db-init db-reset verify lint typecheck test fmt doctor doctor-cpu fetch dates dates-debug inspect ingest search diff drift show regrade check-candidates questions power counterparts recall recall-report recall-compare taxonomy mcp mcp-check site-data site-install site-dev site-build

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
search:  ## make search Q="..." [AS_OF=2026-05-01] [METHOD=hybrid] (no AS_OF = naive)
	$(UV) python -m rb_errata.cli search "$(Q)" $(if $(AS_OF),--as-of $(AS_OF)) $(if $(filter-out naive,$(METHOD)),--method $(METHOD))

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

counterparts:  ## align expected rules to their copies in other versions (needs data/raw)
	$(UV) python -m rb_errata.cli counterparts

# Slice 5. Needs the database and the embedder, no generation: minutes, not hours.
METHOD ?= naive
recall:  ## recall@k for every question: make recall METHOD=as-of|lexical|hybrid; writes evals/runs/
	$(UV) python -m rb_errata.cli recall --method $(METHOD)

recall-compare:  ## pair two runs: make recall-compare A=evals/runs/... B=evals/runs/...
	$(UV) python -m rb_errata.cli recall-compare $(A) $(B)

recall-report:  ## recompute a report offline: make recall-report RUN=evals/runs/recall-...
	$(UV) python -m rb_errata.cli recall-report $(RUN)

taxonomy:  ## categorise every miss in a run (no model): make taxonomy RUN=evals/runs/recall-...
	$(UV) python -m rb_errata.cli taxonomy $(RUN)

mcp:  ## run the MCP server on stdio (what Claude Desktop starts; Ctrl+C to stop)
	$(UV) python -m rb_errata.server

mcp-check:  ## the MCP server over stdio vs the committed snapshot (needs db-up and Ollama)
	$(UV) python -m rb_errata.cli mcp-check

power:  ## how many questions are needed (exact calculation, no model)
	$(UV) python -m rb_errata.cli power

# --- Public site (A33 to A40). Static Next.js in site/; no Riot text. ---

site-data:  ## export numbers-only site/data/results.json from the committed runs
	$(UV) python -m rb_errata.cli site-data

site-install:  ## install the site's exact npm versions (package-lock.json)
	cd site && npm ci

site-dev:  ## run the site locally at http://localhost:3000
	cd site && npm run dev

site-build:  ## build the static site into site/out (what Vercel serves)
	cd site && npm run build
