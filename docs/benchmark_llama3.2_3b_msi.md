Model `llama3.2:3b`, retrieval embedding, 12 questions x 3 runs, top-K 8, distance threshold 1.25, max tokens 400, context 4096, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 42 % (15/36) |
| Fully correct (answer and cited page, or correct refusal) | 33 % (12/36) |
| Correct answers with a warning shown | 8 % (3/36) |
| Silent errors (wrong, no warning) | 42 % (15/36) |
| Flagged errors (wrong, warning shown) | 8 % (3/36) |
| Useless refusals (answer existed) | 8 % (3/36) |
| Correct page cited (among correct answers) | 67 % (6/9) |
| Unstable questions (verdict changes between runs) | 0/12 |
| Median total latency (LLM called) | 0.2 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 0.7 s |
| Median retrieval | 10 ms |
| First LLM load | 2.0 s |
