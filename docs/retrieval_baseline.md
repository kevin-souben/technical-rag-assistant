Retrieval only (no LLM), mode `embedding`, 22 questions, 150 indexed entries, embedding `sentence-transformers/all-MiniLM-L6-v2`, top-K 8, distance threshold 1.25, 2026-10-04

Observation depth: 20 entries. Measured at page level, not passage level.

| ID | Expected page(s) | Rank of first expected page | Distance | Expected page in LLM context | Pages in LLM context |
|---|---|---|---|---|---|
| Q01 | 33 | 1 | 0.70 | yes | 1, 2, 28, 33, 34, 40 |
| Q02 | 16 | 1 | 0.52 | yes | 2, 13, 16, 28, 39 |
| Q03 | 14, 15 | 8 | 1.34 | no | 16, 32 |
| Q04 | 15 | 1 | 1.09 | yes | 13, 15, 16, 28 |
| Q05 | 15 | 2 | 1.15 | yes | 13, 15, 16, 28, 39 |
| Q06 | 33 | 1 | 0.80 | yes | 1, 8, 29, 33 |
| Q07 | 15 | 4 | 1.15 | yes | 13, 14, 15, 16, 28 |
| Q08 | 28 | 1 | 0.66 | yes | 1, 2, 13, 16, 18, 28 |
| Q09 | none (refusal expected) | - | - | blocked before LLM | none |
| Q10 | none (refusal expected) | - | - | blocked before LLM | none |
| Q11 | 39 | 1 | 1.03 | yes | 39 |
| Q12 | 42 | 1 | 0.52 | yes | 5, 41, 42 |
| Q13 | 12 | 1 | 0.86 | yes | 7, 12, 17, 18, 20, 26 |
| Q14 | 14 | 7 | 1.36 | no | none |
| Q15 | 14 | 3 | 1.27 | no | 15 |
| Q16 | 15 | 1 | 1.08 | yes | 13, 15, 16, 28 |
| Q17 | 15 | 1 | 1.12 | yes | 13, 15, 16, 28, 39 |
| Q18 | 14 | 9 | 1.33 | no | 13, 15, 16 |
| Q19 | 14 | 7 | 1.31 | no | 13, 15, 28 |
| Q20 | 14 | 11 | 1.35 | no | 13, 16 |
| Q21 | 14 | 7 | 1.28 | no | 15, 16, 28, 32 |
| Q22 | 15 | 2 | 1.13 | yes | 13, 15, 28 |

| Metric | Result |
|---|---|
| Answerable questions with an expected page in the LLM context | 13/20 |
| Answerable questions with ALL expected pages in the LLM context | 13/20 |
| Answerable questions with an expected page in the 20 first entries | 20/20 |
| Off-topic questions blocked before the LLM | 2/2 |
| Identical results over two runs | yes |
