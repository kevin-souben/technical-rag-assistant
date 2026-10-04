Retrieval only (no LLM), mode `hybrid`, 12 questions, 171 indexed entries, embedding `sentence-transformers/all-MiniLM-L6-v2`, top-K 8, distance threshold 1.25, 2026-10-04

Observation depth: 20 entries. Measured at page level, not passage level.

| ID | Expected page(s) | Rank of first expected page | Distance | Expected page in LLM context | Pages in LLM context |
|---|---|---|---|---|---|
| M01 | 40 | 1 | 0.92 | yes | 5, 6, 22, 40, 46 |
| M02 | 38 | 1 | 0.95 | yes | 2, 18, 19, 33, 38 |
| M03 | 38 | 1 | 1.07 | yes | 2, 5, 19, 38 |
| M04 | 18 | 18 | 1.05 | no | 2, 5, 6, 19, 22, 48 |
| M05 | 28 | 10 | 1.45 | yes | 2, 27, 28, 32, 39, 46, 50 |
| M06 | 17 | 1 | 0.87 | yes | 9, 17, 18 |
| M07 | 20 | > 20 | - | no | 5, 6, 14, 18, 22 |
| M08 | 34 | 1 | 0.98 | yes | 2, 19, 33, 34, 36, 37 |
| M09 | 38 | 1 | 0.77 | yes | 4, 19, 33, 34, 38, 39 |
| M10 | 18 | 1 | 0.88 | yes | 2, 18, 19, 23, 59 |
| M11 | none (refusal expected) | - | - | NOT blocked | 2, 5, 6, 14, 22 |
| M12 | none (refusal expected) | - | - | NOT blocked | 18 |

| Metric | Result |
|---|---|
| Answerable questions with an expected page in the LLM context | 8/10 |
| Answerable questions with ALL expected pages in the LLM context | 8/10 |
| Answerable questions with an expected page in the 20 first entries | 9/10 |
| Off-topic questions blocked before the LLM | 0/2 |
| Identical results over two runs | yes |
