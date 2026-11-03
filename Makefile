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

.PHONY: help install db-up db-down db-init db-reset verify lint typecheck test fmt doctor doctor-cpu fetch dates dates-debug inspect ingest search diff drift show regrade check-candidates questions power counterparts recall recall-report recall-compare taxonomy mcp mcp-check check-updates add-version version-impact answers answer-sample judge answers-report confidence agent-run agent-compare ask phoenix-up phoenix-down injection injection-report app-install app-build app app-dev site-data site-install site-dev site-build

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

answers:  ## slice 11: answer every question (GPU per A41): make answers [LIMIT=5] [RESUME=evals/runs/answers-...]
	$(UV) python -m rb_errata.cli answers $(if $(LIMIT),--limit $(LIMIT),) $(if $(RESUME),--resume $(RESUME),)

answer-sample:  ## the blind hand-label sample: make answer-sample RUN=evals/runs/answers-...
	$(UV) python -m rb_errata.cli answer-sample $(RUN)

judge:  ## LLM judge over a run, then the report: make judge RUN=evals/runs/answers-...
	$(UV) python -m rb_errata.cli judge $(RUN)

answers-report:  ## accuracy and kappa, offline: make answers-report RUN=evals/runs/answers-...
	$(UV) python -m rb_errata.cli answers-report $(RUN)

confidence:  ## slice 13: confidence score and calibration: make confidence RUN=evals/runs/answers-...
	$(UV) python -m rb_errata.cli confidence $(RUN) $(if $(JUDGE),--judge $(JUDGE),)

agent-run:  ## slice 14: the agent over every question: make agent-run CONF=evals/runs/answers-.../confidence.json
	$(UV) python -m rb_errata.cli agent-run $(if $(CONF),--conf $(CONF),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(RESUME),--resume $(RESUME),)

agent-compare:  ## agent vs slice 11, paired: make agent-compare A=evals/runs/answers-... B=evals/runs/agent-...
	$(UV) python -m rb_errata.cli agent-compare $(A) $(B) $(if $(JUDGE),--judge $(JUDGE),)

ask:  ## ask the agent: make ask Q="..." [AS_OF=2026-05-01] [CONF=.../confidence.json]
	$(UV) python -m rb_errata.cli ask "$(Q)" $(if $(AS_OF),--as-of $(AS_OF),) $(if $(CONF),--conf $(CONF),)

phoenix-up:  ## start Arize Phoenix at http://localhost:6006 (traces when RB_TRACE_ENDPOINT is set)
	docker compose --profile trace up -d phoenix

phoenix-down:  ## stop Phoenix (its trace store is kept)
	docker compose --profile trace stop phoenix

injection:  ## slice 16: 5 planted-passage attacks x 4 prompts x 20 questions (GPU per A41)
	$(UV) python -m rb_errata.cli injection

injection-report:  ## recompute: make injection-report RUN=evals/runs/injection-...
	$(UV) python -m rb_errata.cli injection-report $(RUN)

app-install:  ## slice 17: install the local app's exact npm versions (app/package-lock.json)
	cd app && npm ci

app-build:  ## build the local app's front end into app/dist
	cd app && npm run build

app:  ## run the local app at http://localhost:8765 (needs db-up and Ollama; Ctrl+C to stop)
	$(UV) python -m rb_errata.app

app-dev:  ## front-end development with hot reload at http://localhost:5173 (run `make app` too)
	cd app && npm run dev

check-updates:  ## is a newer Core Rules version out? (mirror manifest + Riot Rules Hub; exit 1 if so)
	$(UV) python -m rb_errata.cli check-updates

add-version:  ## register a new version: make add-version V=1.5 NOTES=https://playriftbound.com/...
	$(UV) python -m rb_errata.cli add-version $(V) --notes "$(NOTES)"

version-impact:  ## what a version changes and which labels cite it: make version-impact V=1.5
	$(UV) python -m rb_errata.cli version-impact $(V)

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
