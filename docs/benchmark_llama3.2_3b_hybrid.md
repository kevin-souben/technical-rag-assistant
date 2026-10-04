Model `llama3.2:3b`, retrieval hybrid, 27 questions x 3 runs, top-K 8, distance threshold 1.25, max tokens 400, context 4096, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 81 % (66/81) |
| Fully correct (answer and cited page, or correct refusal) | 67 % (54/81) |
| Correct answers with a warning shown | 22 % (18/81) |
| Silent errors (wrong, no warning) | 10 % (8/81) |
| Flagged errors (wrong, warning shown) | 5 % (4/81) |
| Useless refusals (answer existed) | 4 % (3/81) |
| Correct page cited (among correct answers) | 80 % (48/60) |
| Unstable questions (verdict changes between runs) | 1/27 |
| Median total latency (LLM called) | 0.4 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 4.7 s |
| Median retrieval | 18 ms |
| First LLM load | 1.0 s |
