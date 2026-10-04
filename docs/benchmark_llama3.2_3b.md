Model `llama3.2:3b`, retrieval embedding, 22 questions x 3 runs, top-K 8, distance threshold 1.25, max tokens 400, context 4096, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 55 % (36/66) |
| Fully correct (answer and cited page, or correct refusal) | 50 % (33/66) |
| Correct answers with a warning shown | 9 % (6/66) |
| Silent errors (wrong, no warning) | 3 % (2/66) |
| Flagged errors (wrong, warning shown) | 20 % (13/66) |
| Useless refusals (answer existed) | 23 % (15/66) |
| Correct page cited (among correct answers) | 90 % (27/30) |
| Unstable questions (verdict changes between runs) | 1/22 |
| Median total latency (LLM called) | 0.3 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 1.5 s |
| Median retrieval | 10 ms |
| First LLM load | 1.6 s |
