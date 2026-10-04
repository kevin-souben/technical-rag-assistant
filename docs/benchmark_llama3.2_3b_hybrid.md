Model `llama3.2:3b`, retrieval hybrid, 22 questions x 3 runs, top-K 8, distance threshold 1.25, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 82 % (54/66) |
| Fully correct (answer and cited page, or correct refusal) | 64 % (42/66) |
| Correct answers with a warning shown | 27 % (18/66) |
| Silent errors (wrong, no warning) | 9 % (6/66) |
| Flagged errors (wrong, warning shown) | 5 % (3/66) |
| Useless refusals (answer existed) | 5 % (3/66) |
| Correct page cited (among correct answers) | 75 % (36/48) |
| Unstable questions (verdict changes between runs) | 0/22 |
| Median total latency (LLM called) | 0.4 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 58.2 s |
| Median retrieval | 18 ms |
| First LLM load | 1.0 s |
