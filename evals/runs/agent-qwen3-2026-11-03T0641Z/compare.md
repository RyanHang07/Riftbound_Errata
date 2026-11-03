# Agent agent-qwen3-2026-11-03T0641Z against answers-qwen3-2026-11-03T0511Z

Paired by question on judge verdicts (correct vs not); exact two-sided McNemar.

| questions | without loop | with loop | gained | lost | McNemar p |
|---|---|---|---|---|---|
| all | 101/224 = 45% [39%, 52%] | 112/224 = 50% [44%, 56%] | 22 | 11 | 0.0801 |
| expert-ruling | 64/160 = 40% [33%, 48%] | 73/160 = 46% [38%, 53%] | 15 | 6 | 0.0784 |
| expert-ruling-faq | 0/8 = 0% [0%, 32%] | 2/8 = 25% [7%, 59%] | 2 | 0 | 0.5 |
| version-change | 37/56 = 66% [53%, 77%] | 37/56 = 66% [53%, 77%] | 5 | 5 | 1 |
| re-searched only | 26/105 = 25% [17%, 34%] | 35/105 = 33% [25%, 43%] | 15 | 6 | 0.0784 |

Re-search fired on 105/224 = 47% [40%, 53%] of questions.

## Router (names a specific card?) against each ruling's source category

Accuracy 134/168 = 80% [73%, 85%]; unparsed 0; card questions routed as rules-only: 20.

## Generation time (Ollama's own clock, prefill + decode)

Without loop: total 474 s, median 1.91 s. With loop (route call on every question, second answer when re-searched): total 1060 s, median 3.35 s (+123%).
