Retrieval only (no LLM), mode `embedding`, 12 questions, 171 indexed entries, embedding `sentence-transformers/all-MiniLM-L6-v2`, top-K 8, distance threshold 1.25, 2026-10-04

Observation depth: 20 entries. Measured at page level, not passage level.

| ID | Expected page(s) | Rank of first expected page | Distance | Expected page in LLM context | Pages in LLM context |
|---|---|---|---|---|---|
| M01 | 40 | 4 | 0.92 | yes | 5, 6, 14, 18, 22, 40, 46 |
| M02 | 38 | 3 | 0.89 | yes | 12, 19, 20, 26, 27, 38 |
| M03 | 38 | 1 | 0.89 | yes | 2, 12, 19, 38 |
| M04 | 18 | 6 | 1.05 | yes | 2, 5, 12, 14, 18, 19, 22 |
| M05 | 28 | > 20 | - | no | 2, 12, 18, 27, 32, 46, 50, 51 |
| M06 | 17 | 1 | 0.87 | yes | 9, 17, 18 |
| M07 | 20 | > 20 | - | no | 5, 6, 14, 18, 22 |
| M08 | 34 | 4 | 0.98 | yes | 2, 12, 14, 19, 33, 34, 36 |
| M09 | 38 | 1 | 0.77 | yes | 2, 12, 19, 33, 38, 41 |
| M10 | 18 | 1 | 0.88 | yes | 2, 18, 49 |
| M11 | none (refusal expected) | - | - | NOT blocked | 5, 6, 14, 18, 22, 46 |
| M12 | none (refusal expected) | - | - | NOT blocked | 18 |

| Metric | Result |
|---|---|
| Answerable questions with an expected page in the LLM context | 8/10 |
| Answerable questions with ALL expected pages in the LLM context | 8/10 |
| Answerable questions with an expected page in the 20 first entries | 8/10 |
| Off-topic questions blocked before the LLM | 0/2 |
| Identical results over two runs | yes |
