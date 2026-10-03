Model `llama3.2:3b`, 13 questions x 3 runs, top-K 8, distance threshold 1.25, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 69 % (27/39) |
| Fully correct (answer and cited page, or correct refusal) | 62 % (24/39) |
| Silent errors (wrong, no warning) | 13 % (5/39) |
| Flagged errors (wrong, warning shown) | 8 % (3/39) |
| Useless refusals (answer existed) | 10 % (4/39) |
| Correct page cited (among correct answers) | 86 % (18/21) |
| Unstable questions (verdict changes between runs) | 1/13 |
| Median total latency (LLM called) | 0.3 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 1.5 s |
| Median retrieval | 10 ms |
| First LLM load | 1.2 s |
