# MCP check against recall-as-of-qwen3-2026-11-03T0304Z

Server over stdio (`python -m rb_errata.server`); tools: ask, get_rule, list_versions, search_rules, what_changed.
Captured 2026-11-04T1806Z.

## Parity: same top-5 refs, same order

224 of 224 identical; 0 differ; 0 errors.

| stratum | recall@5 via server | snapshot |
|---|---|---|
| expert-ruling | 100/160 = 62% [55%, 70%] | 100/160 = 62% [55%, 70%] |
| expert-ruling-faq | 3/8 = 38% [14%, 69%] | 3/8 = 38% [14%, 69%] |
| version-change | 45/56 = 80% [68%, 89%] | 45/56 = 80% [68%, 89%] |

## Timing (seconds, client side, includes the pipe)

search_rules: first call 0.31; warm median 0.037, p90 0.042.
- get_rule: 3.07
- get_rule: 0.00
- what_changed: 2.40
(The calls above use core@1.4:419.4.a; the first get_rule parses v1.4, what_changed parses v1.3.)
