# IFAB RAG retrieval evaluation

Golden set: **20** VAR/offside questions mapped to the governing IFAB Law, run against the real `LawRetriever` (bm25 (offline)). Metrics computed directly (no RAGAS dep).

| Metric | Score |
|---|---|
| Hit-Rate@1 | 0.90 |
| Hit-Rate@3 | 1.00 |
| Hit-Rate@5 | 1.00 |
| MRR | 0.942 |

## Per-Law

| Law | n | Hit@1 | Hit@5 |
|---|---|---|---|
| 5 | 1 | 0/1 | 1/1 |
| 7 | 1 | 1/1 | 1/1 |
| 11 | 8 | 8/8 | 8/8 |
| 12 | 2 | 2/2 | 2/2 |
| 13 | 1 | 1/1 | 1/1 |
| 14 | 2 | 1/2 | 2/2 |
| 15 | 1 | 1/1 | 1/1 |
| 16 | 1 | 1/1 | 1/1 |
| 17 | 1 | 1/1 | 1/1 |
| VAR | 2 | 2/2 | 2/2 |

## Misroutes (top-1 != true Law)

| Question | True | Top-1 | Rank of true |
|---|---|---|---|
| Did the goalkeeper come off the goal line before the penalty was taken? | 14 | 16 | 2 |
| Does the referee have final authority over the decision? | 5 | VAR | 3 |
