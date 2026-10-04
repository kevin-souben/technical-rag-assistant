Retrieval only (no LLM), mode `hybrid`, 27 questions, 150 indexed entries, embedding `sentence-transformers/all-MiniLM-L6-v2`, top-K 8, distance threshold 1.25, 2026-10-04

Observation depth: 20 entries. Measured at page level, not passage level.

| ID | Expected page(s) | Rank of first expected page | Distance | Expected page in LLM context | Pages in LLM context |
|---|---|---|---|---|---|
| Q01 | 33 | 1 | 0.70 | yes | 2, 16, 28, 29, 33 |
| Q02 | 16 | 1 | 0.52 | yes | 2, 6, 16, 28 |
| Q03 | 14, 15 | 3 | 1.34 | yes | 14, 15, 16, 32 |
| Q04 | 15 | 1 | 1.09 | yes | 13, 15, 16, 19, 28 |
| Q05 | 15 | 2 | 1.15 | yes | 13, 15, 16, 19, 28 |
| Q06 | 33 | 1 | 0.80 | yes | 8, 28, 29, 33 |
| Q07 | 15 | 1 | 1.15 | yes | 13, 15, 16, 28 |
| Q08 | 28 | 1 | 0.66 | yes | 2, 6, 8, 16, 28 |
| Q09 | none (refusal expected) | - | - | blocked before LLM | none |
| Q10 | none (refusal expected) | - | - | blocked before LLM | none |
| Q11 | 39 | 1 | 1.03 | yes | 7, 39 |
| Q12 | 42 | 1 | 0.52 | yes | 5, 41, 42 |
| Q13 | 12 | 1 | 0.86 | yes | 7, 12, 17, 20, 26 |
| Q14 | 14 | 3 | 1.36 | yes | 4, 14, 15, 19, 28, 29 |
| Q15 | 14 | 2 | 1.27 | yes | 4, 14, 15, 19, 28, 29 |
| Q16 | 15 | 2 | 1.08 | yes | 13, 15, 16, 28 |
| Q17 | 15 | 1 | 1.12 | yes | 13, 15, 16, 19, 28 |
| Q18 | 14 | 9 | 1.36 | yes | 13, 14, 15, 16, 19, 28, 29 |
| Q19 | 14 | 5 | 1.36 | yes | 13, 14, 15, 19, 28, 29 |
| Q20 | 14 | 5 | 1.38 | yes | 4, 13, 14, 15, 16, 19, 28 |
| Q21 | 14 | 2 | 1.28 | yes | 14, 15, 16, 19, 28, 32 |
| Q22 | 15 | 2 | 1.13 | yes | 4, 13, 15, 19, 28, 29 |
| Q23 | 34 | 1 | 0.80 | yes | 22, 27, 34 |
| Q24 | 27 | 1 | 0.78 | yes | 26, 27, 29 |
| Q25 | 32 | 1 | 0.96 | yes | 32 |
| Q26 | 10, 17 | 1 | 0.74 | yes | 8, 16, 17, 18 |
| Q27 | 30 | 1 | 0.59 | yes | 8, 17, 23, 30 |

| Metric | Result |
|---|---|
| Answerable questions with an expected page in the LLM context | 25/25 |
| Answerable questions with ALL expected pages in the LLM context | 24/25 |
| Answerable questions with an expected page in the 20 first entries | 25/25 |
| Off-topic questions blocked before the LLM | 2/2 |
| Identical results over two runs | yes |
