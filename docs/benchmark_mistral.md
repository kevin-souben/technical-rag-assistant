Model `mistral`, 13 questions x 3 runs, top-K 8, distance threshold 1.25, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 69 % (27/39) |
| Fully correct (answer and cited page, or correct refusal) | 62 % (24/39) |
| Silent errors (wrong, no warning) | 15 % (6/39) |
| Flagged errors (wrong, warning shown) | 8 % (3/39) |
| Useless refusals (answer existed) | 8 % (3/39) |
| Correct page cited (among correct answers) | 86 % (18/21) |
| Unstable questions (verdict changes between runs) | 0/13 |
| Median total latency (LLM called) | 0.7 s |
| Median first token (LLM called) | 0.1 s |
| Max total latency | 2.8 s |
| Median retrieval | 11 ms |
| First LLM load | 4.9 s |
