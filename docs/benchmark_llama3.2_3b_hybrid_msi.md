Model `llama3.2:3b`, retrieval hybrid, 12 questions x 3 runs, top-K 8, distance threshold 1.25, max tokens 400, context 4096, 2026-10-04

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 58 % (21/36) |
| Fully correct (answer and cited page, or correct refusal) | 58 % (21/36) |
| Correct answers with a warning shown | 0 % (0/36) |
| Silent errors (wrong, no warning) | 25 % (9/36) |
| Flagged errors (wrong, warning shown) | 8 % (3/36) |
| Useless refusals (answer existed) | 8 % (3/36) |
| Correct page cited (among correct answers) | 100 % (15/15) |
| Unstable questions (verdict changes between runs) | 0/12 |
| Median total latency (LLM called) | 0.3 s |
| Median first token (LLM called) | 0.0 s |
| Max total latency | 0.9 s |
| Median retrieval | 18 ms |
| First LLM load | 1.4 s |
