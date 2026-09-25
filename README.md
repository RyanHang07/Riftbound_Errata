# rb_errata

Answers rules questions for Riot's Riftbound TCG correctly **as of a date**.

The published corpus contradicts itself across versions. A naive retrieval
system answers a July 2026 question with December 2025 rules, confidently and
with citations. This project measures that failure, then fixes it with
version-aware retrieval, against a labelled question set.

The full specification is [`docs/BRIEF.md`](docs/BRIEF.md). Read its
**Amendments** section too: those decisions override the original text.

## Status

| Slice | | State |
|:--|:--|:--|
| 0 | Setup: `make verify` and `doctor` | done |
| 1 | Corpus availability spike (**a gate**: if versioned rules are unobtainable, the thesis dies) | next |

## Setup

Needs Python 3.12, [uv](https://docs.astral.sh/uv/), Docker with Compose v2,
and [Ollama](https://ollama.com) 0.9 or newer. Runs fully offline once the
models are pulled.

```bash
cp .env.example .env
make install                 # exact versions from uv.lock
make db-up                   # Postgres 17 + pgvector on localhost:5433
ollama pull nomic-embed-text
ollama pull qwen3:4b
make verify                  # free: lint, typecheck, contract tests
make doctor                  # real database and models, no corpus
make doctor-cpu              # same, models kept off the GPU: target numbers
```

The first `make doctor` **fails on purpose**: the model digests aren't pinned
yet. It prints the digest it observed; paste each into `.env`
(`RB_EMBED_DIGEST`, `RB_GEN_DIGEST`) and run it again. After that, a model tag
that quietly starts pointing at different weights fails doctor instead of
changing every result.

## Legal

Card and rules text are Riot Games' intellectual property and are **not**
stored in this repository. Only hashes and metadata are committed (see
[`data/README.md`](data/README.md)). The fan content terms get checked in
slice 1, before any public distribution, and this section will record what
they require.
