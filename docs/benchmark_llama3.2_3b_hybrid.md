Model `llama3.2:3b`, retrieval hybrid, 17 questions x 3 runs, top-K 8, distance threshold 1.25, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 82 % (42/51) |
| Fully correct (answer and cited page, or correct refusal) | 65 % (33/51) |
| Correct answers with a warning shown | 29 % (15/51) |
| Silent errors (wrong, no warning) | 12 % (6/51) |
| Flagged errors (wrong, warning shown) | 0 % (0/51) |
| Useless refusals (answer existed) | 6 % (3/51) |
| Correct page cited (among correct answers) | 75 % (27/36) |
| Unstable questions (verdict changes between runs) | 0/17 |
| Median total latency (LLM called) | 0.4 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 1.3 s |
| Median retrieval | 16 ms |
| First LLM load | 1.0 s |
