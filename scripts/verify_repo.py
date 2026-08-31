"""Self-check: confirm the repository is internally consistent and reproduces
the headline numbers reported in the paper.

Run this after any change to data/ or results/, and before depositing.

  python3 scripts/verify_repo.py
"""
from __future__ import annotations

import csv
import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Headline values as published in the paper.
PAPER = {"claude_mean_mmri": 0.172, "gpt_mean_mmri": 0.464, "model_pearson_r": 0.578}
TOL = 0.001

checks: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    checks.append((cond, label))


def rd(rel: str) -> list[dict]:
    with (REPO / rel).open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def pearson(a: list[float], b: list[float]) -> float:
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return num / den


def main() -> int:
    # ---- shape
    meta = rd("data/report_metadata.csv")
    cov = rd("data/coverage_scores.csv")
    covg = rd("data/coverage_scores_gpt.csv")
    mmri = rd("data/mmri_results.csv")
    comp = rd("data/model_comparison.csv")
    human = rd("data/human_annotations.csv")
    topics = rd("data/sasb_topics.csv")

    check(len(meta) == 20, "report_metadata.csv has 20 reports")
    check(len(topics) == 6, "sasb_topics.csv has 6 SASB topics")
    check(len(cov) == 120, "coverage_scores.csv has 120 cells (20x6)")
    check(len(covg) == 120, "coverage_scores_gpt.csv has 120 cells")
    check(len(mmri) == 20, "mmri_results.csv has 20 reports")
    check(len(comp) == 20, "model_comparison.csv has 20 reports")
    check(len(human) == 30, "human_annotations.csv has 30 annotated cells")

    check(len(list((REPO / "results/claude/per_cell").glob("*.json"))) == 120,
          "results/claude/per_cell has 120 model responses")
    check(len(list((REPO / "results/gpt/per_cell").glob("*.json"))) == 120,
          "results/gpt/per_cell has 120 model responses")

    # ---- internal consistency
    check(all(abs((float(r["presence"]) + float(r["specificity"]) + float(r["quantification"])) / 3
                  - float(r["coverage"])) < 1e-3 for r in cov),
          "coverage == mean(P,S,Q) for every Claude cell")
    check(all(abs(float(r["coverage"]) + float(r["misalignment"]) - 1) < 1e-3 for r in cov),
          "misalignment == 1 - coverage for every Claude cell")

    allowed = {0.0, 0.25, 0.5, 0.75, 1.0}
    check(all(float(r[d]) in allowed for r in cov
              for d in ("presence", "specificity", "quantification")),
          "all Claude P/S/Q values sit on the 5-point anchor scale")

    ids_meta = {r["report_id"] for r in meta}
    check({r["report_id"] for r in cov} == ids_meta,
          "coverage_scores.csv report_ids match report_metadata.csv")
    check({r["report_id"] for r in mmri} == ids_meta,
          "mmri_results.csv report_ids match report_metadata.csv")

    # a_i must agree with the climate_only flag in the metadata
    climate_only = {r["report_id"] for r in meta if r["climate_only"] == "1"}
    zeroed = {r["report_id"] for r in cov if r["a_i"] == "0"}
    check(zeroed == climate_only,
          "a_i=0 cells occur in exactly the reports flagged climate_only")

    # evidence chunk ids must cover every cell that has evidence
    ev = rd("data/retrieved_evidence.csv")
    check({(r["report_id"], r["topic"]) for r in ev} <= {(r["report_id"], r["topic"]) for r in cov},
          "retrieved_evidence.csv cells are a subset of scored cells")

    # Citations in per-cell responses should reference chunks that were actually
    # retrieved for that cell. A small residue does not: the scoring models
    # occasionally cite a neighbouring chunk id. This is a known, bounded
    # property of the released data (see docs/KNOWN_ISSUES.md), so it is
    # reported as a rate and only fails if it exceeds the documented ceiling.
    CITATION_DRIFT_CEILING = 0.02          # 2% of all citations
    known = {r["chunk_id"] for r in ev}
    for model in ("claude", "gpt"):
        total = dangling = 0
        for f in (REPO / f"results/{model}/per_cell").glob("*.json"):
            cits = json.loads(f.read_text()).get("citations", [])
            total += len(cits)
            dangling += sum(1 for c in cits if c not in known)
        rate = dangling / total if total else 0.0
        check(rate <= CITATION_DRIFT_CEILING,
              f"{model} citation drift {dangling}/{total} = {rate:.2%} "
              f"(documented ceiling {CITATION_DRIFT_CEILING:.0%})")

    # ---- headline numbers
    mm_key = next(k for k in mmri[0] if k.upper().startswith("MMRI"))
    cl = [float(r[mm_key]) for r in mmri]
    check(abs(st.mean(cl) - PAPER["claude_mean_mmri"]) < TOL,
          f"Claude mean MMRI = {st.mean(cl):.4f} (paper: {PAPER['claude_mean_mmri']})")

    gc = [float(r["mmri_claude"]) for r in comp]
    gg = [float(r["mmri_gpt"]) for r in comp]
    check(abs(st.mean(gg) - PAPER["gpt_mean_mmri"]) < TOL,
          f"GPT mean MMRI = {st.mean(gg):.4f} (paper: {PAPER['gpt_mean_mmri']})")
    check(abs(pearson(gc, gg) - PAPER["model_pearson_r"]) < TOL,
          f"Claude-GPT Pearson r = {pearson(gc, gg):.4f} (paper: {PAPER['model_pearson_r']})")

    # ---- corpus provenance (warn only; URLs are filled in before deposit)
    no_url = [r["report_id"] for r in meta if not r["source_url"].strip()]

    # ---- report
    width = max(len(m) for _, m in checks)
    for ok, msg in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {msg:<{width}}")
    failed = sum(1 for ok, _ in checks if not ok)
    print(f"\n{len(checks) - failed}/{len(checks)} checks passed")

    if no_url:
        print(f"\nNOTE: {len(no_url)} report(s) still have an empty source_url in "
              f"data/report_metadata.csv.\n      Fill these in before depositing — see docs/CORPUS.md.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
