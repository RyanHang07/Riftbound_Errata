# Determinism determinism-2026-11-04T2223Z

10 prompts x 3 repeats, temperature 0.0, seed 42.

| mode | GPU share | identical on every repeat | first answer = control's repeat 2 | s per answer |
|---|---|---|---|---|
| gpu | 100% | 4 of 10 | control | 2.69 |
| gpu-warm | 100% | 10 of 10 | 10 of 10 | 2.21 |
| cpu-warm | 0% | 10 of 10 | 1 of 10 | 24.19 |
