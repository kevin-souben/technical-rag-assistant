Model `llama3.2:3b`, retrieval embedding, 27 questions x 3 runs, top-K 8, distance threshold 1.25, max tokens 400, context 4096, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 56 % (45/81) |
| Fully correct (answer and cited page, or correct refusal) | 52 % (42/81) |
| Correct answers with a warning shown | 7 % (6/81) |
| Silent errors (wrong, no warning) | 10 % (8/81) |
| Flagged errors (wrong, warning shown) | 15 % (12/81) |
| Useless refusals (answer existed) | 20 % (16/81) |
| Correct page cited (among correct answers) | 92 % (36/39) |
| Unstable questions (verdict changes between runs) | 2/27 |
| Median total latency (LLM called) | 0.3 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 1.5 s |
| Median retrieval | 11 ms |
| First LLM load | 3.9 s |
