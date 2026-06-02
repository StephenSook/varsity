"""Honest RAG retrieval evaluation over the IFAB Law corpus.

Runs the real LawRetriever against a golden set of VAR/offside questions mapped to the
governing Law, and reports Hit-Rate@1/3/5 and MRR (overall + per Law), plus a
predicted-vs-true confusion list. No heavy RAGAS dependency: the metrics are computed
directly, so this runs in CI on the offline keyword path and live on the Granite+FAISS
path. The committed report (docs/benchmarks/rag-eval.md) is a judge-facing artifact.

    python -m evals.run_eval               # offline keyword path (CI-safe)
    python -m evals.run_eval --embeddings  # online Granite + FAISS (needs watsonx creds)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from app.rag.retriever import LawRetriever

GOLDEN = Path(__file__).resolve().parent / "golden.jsonl"
SCORES = Path(__file__).resolve().parent / "scores.json"
REPORT = Path(__file__).resolve().parents[2] / "docs" / "benchmarks" / "rag-eval.md"


@dataclass
class EvalResult:
    n: int
    hit_at_1: float
    hit_at_3: float
    hit_at_5: float
    mrr: float
    per_law: dict
    misroutes: list
    path: str


def load_golden(path: Path = GOLDEN) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def evaluate(
    retriever: LawRetriever,
    golden: list[dict],
    *,
    k: int = 5,
    use_embeddings: bool = False,
) -> EvalResult:
    hits = {1: 0, 3: 0, 5: 0}
    rr = 0.0
    per_law: dict[str, dict] = {}
    misroutes: list[dict] = []
    for ex in golden:
        true = ex["law"]
        top = retriever.rank(ex["q"], k=max(k, 5), use_embeddings=use_embeddings)
        ranked = [c.law for c in top]
        top1 = ranked[0] if ranked else None
        rank_of_true = next((i + 1 for i, law in enumerate(ranked) if law == true), None)
        for kk in (1, 3, 5):
            if rank_of_true and rank_of_true <= kk:
                hits[kk] += 1
        rr += (1.0 / rank_of_true) if rank_of_true else 0.0
        pl = per_law.setdefault(true, {"n": 0, "hit1": 0, "hit5": 0})
        pl["n"] += 1
        pl["hit1"] += 1 if rank_of_true == 1 else 0
        pl["hit5"] += 1 if (rank_of_true and rank_of_true <= 5) else 0
        if top1 != true:
            misroutes.append(
                {"q": ex["q"], "true": true, "top1": top1, "rank_of_true": rank_of_true}
            )
    n = len(golden)
    return EvalResult(
        n=n,
        hit_at_1=hits[1] / n,
        hit_at_3=hits[3] / n,
        hit_at_5=hits[5] / n,
        mrr=rr / n,
        per_law=per_law,
        misroutes=misroutes,
        path="granite-faiss (online)" if use_embeddings else "bm25 (offline)",
    )


def _render_markdown(r: EvalResult) -> str:
    lines = [
        "# IFAB RAG retrieval evaluation",
        "",
        f"Golden set: **{r.n}** VAR/offside questions mapped to the governing IFAB Law, run "
        f"against the real `LawRetriever` ({r.path}). Metrics computed directly (no RAGAS dep).",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| Hit-Rate@1 | {r.hit_at_1:.2f} |",
        f"| Hit-Rate@3 | {r.hit_at_3:.2f} |",
        f"| Hit-Rate@5 | {r.hit_at_5:.2f} |",
        f"| MRR | {r.mrr:.3f} |",
        "",
        "## Per-Law",
        "",
        "| Law | n | Hit@1 | Hit@5 |",
        "|---|---|---|---|",
    ]
    for law in sorted(r.per_law, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else 0)):
        pl = r.per_law[law]
        lines.append(f"| {law} | {pl['n']} | {pl['hit1']}/{pl['n']} | {pl['hit5']}/{pl['n']} |")
    lines += ["", "## Misroutes (top-1 != true Law)", ""]
    if r.misroutes:
        lines += ["| Question | True | Top-1 | Rank of true |", "|---|---|---|---|"]
        for m in r.misroutes:
            rank = m["rank_of_true"] or "miss"
            lines.append(f"| {m['q']} | {m['true']} | {m['top1']} | {rank} |")
    else:
        lines.append("None: every question routed to the correct Law at rank 1.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate IFAB RAG retrieval.")
    parser.add_argument(
        "--embeddings", action="store_true", help="use the Granite+FAISS online path"
    )
    args = parser.parse_args()

    golden = load_golden()
    result = evaluate(LawRetriever(), golden, use_embeddings=args.embeddings)
    print(
        f"[{result.path}] n={result.n} "
        f"Hit@1={result.hit_at_1:.2f} Hit@3={result.hit_at_3:.2f} "
        f"Hit@5={result.hit_at_5:.2f} MRR={result.mrr:.3f} misroutes={len(result.misroutes)}"
    )
    SCORES.write_text(
        json.dumps(
            {
                "path": result.path,
                "n": result.n,
                "hit_at_1": round(result.hit_at_1, 4),
                "hit_at_3": round(result.hit_at_3, 4),
                "hit_at_5": round(result.hit_at_5, 4),
                "mrr": round(result.mrr, 4),
                "per_law": result.per_law,
            },
            indent=2,
        )
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(_render_markdown(result))
    print(f"wrote {SCORES} and {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
