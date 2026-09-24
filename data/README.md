# data/

What is committed here, and what never is.

| Path | Committed | Contents |
|:--|:--|:--|
| `raw/` | **never** (gitignored) | Fetched corpus: Riot's copyrighted text |
| `corpus.json` | yes, from slice 2 | Everything about the corpus except the corpus: source, ref, validity window, content hash, token count, embedding model tag and digest |
| `eval_runs.json` | yes, from slice 5 | Eval results, with the full settings record of each run |

The ingestion and serving path writes these files. The eval and analysis path
reads only these files. That way every figure in the writeup can be recomputed
by someone without credentials and without the rulebook.
