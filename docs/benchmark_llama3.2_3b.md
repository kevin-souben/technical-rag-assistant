Model `llama3.2:3b`, retrieval embedding, 17 questions x 3 runs, top-K 8, distance threshold 1.25, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 65 % (33/51) |
| Fully correct (answer and cited page, or correct refusal) | 59 % (30/51) |
| Correct answers with a warning shown | 12 % (6/51) |
| Silent errors (wrong, no warning) | 6 % (3/51) |
| Flagged errors (wrong, warning shown) | 16 % (8/51) |
| Useless refusals (answer existed) | 14 % (7/51) |
| Correct page cited (among correct answers) | 89 % (24/27) |
| Unstable questions (verdict changes between runs) | 1/17 |
| Median total latency (LLM called) | 0.2 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 1.0 s |
| Median retrieval | 10 ms |
| First LLM load | 1.2 s |
