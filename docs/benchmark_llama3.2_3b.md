Model `llama3.2:3b`, retrieval embedding, 22 questions x 3 runs, top-K 8, distance threshold 1.25, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 50 % (33/66) |
| Fully correct (answer and cited page, or correct refusal) | 45 % (30/66) |
| Correct answers with a warning shown | 9 % (6/66) |
| Silent errors (wrong, no warning) | 8 % (5/66) |
| Flagged errors (wrong, warning shown) | 18 % (12/66) |
| Useless refusals (answer existed) | 24 % (16/66) |
| Correct page cited (among correct answers) | 89 % (24/27) |
| Unstable questions (verdict changes between runs) | 2/22 |
| Median total latency (LLM called) | 0.2 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 1.5 s |
| Median retrieval | 11 ms |
| First LLM load | 3.7 s |
