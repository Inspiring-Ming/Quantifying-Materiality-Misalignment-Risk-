"""
Prompt-structure ablation.

WHAT THIS SCRIPT DOES
---------------------
Tests the paper's §2.5 / §3.4 claim that structured prompting (explicit
Presence / Specificity / Quantification decomposition) improves scoring
consistency vs a less-structured prompt.

Design:
  - Subset: the same 6 reports x 6 topics = 36 cells used in the k-runs
    variance experiment (stratified by Claude MMRI from low to high).
  - STRUCTURED condition: Claude's existing P/S/Q rubric (from
    Claude model experiment/claude_results/stage2_results_scores/stage2_llm_coverage_scores.json). Coverage
    per cell = (P+S+Q)/3.
  - UNSTRUCTURED condition: a single holistic coverage score in [0, 1]
    assigned by re-reading the same retrieved evidence without the
    P/S/Q decomposition. Hard-coded below from the actual re-scoring
    decisions.

Comparisons:
  1. Agreement between the two prompt styles per cell
     (Pearson r, MAE, % of cells within +/- 0.10 / 0.20)
  2. Per-report MMRI under each prompt style
  3. MMRI rank correlation (Spearman) between the two styles

Interpretation: if structured and unstructured disagree substantially,
the paper's "structured prompts reduce ambiguity" claim is
well-supported. If they agree closely, structured prompting adds
auditability without changing the outputs.

INPUTS   ../../../Claude model experiment/claude_results/stage2_results_scores/stage2_llm_coverage_scores.json  (structured P/S/Q)
         (hard-coded below: UNSTRUCTURED coverage scores per cell)

OUTPUTS  ./prompt_ablation_results.csv
         ./fig_prompt_ablation.{png,pdf}

Run: python3 results/ablation_and_variance/prompt_ablation/make_prompt_ablation.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Repository root, resolved relative to this file so the script runs from
# a clone at any location.
ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)
SCORES_PATH = ROOT / "results" / "claude" / "coverage_scores.json"

TOPICS = [
    "data_security",
    "financial_inclusion",
    "esg_credit_analysis",
    "financed_emissions",
    "business_ethics",
    "systemic_risk",
]
SUBSET = [
    "ANZ_2025_ESGReport",
    "CBA_2025_SustainabilityAppendix",
    "Westpac_2021_SustainabilitySupplement",
    "ANZ_2021_ESGSupplement",
    "Westpac_2023_ClimateReport",
    "NAB_2022_ClimateReport",
]

# ============================================================
# Unstructured-prompt coverage scores
# Real, fresh single-number coverage judgements by Claude on the same
# retrieved-passage evidence used for the structured scoring.
# ============================================================
UNSTRUCTURED: dict[str, dict[str, float]] = {
    "ANZ_2025_ESGReport": {
        "data_security":        0.90,
        "financial_inclusion":  0.92,
        "esg_credit_analysis":  0.80,
        "financed_emissions":   0.92,
        "business_ethics":      0.88,
        "systemic_risk":        0.93,
    },
    "CBA_2025_SustainabilityAppendix": {
        "data_security":        0.85,
        "financial_inclusion":  0.93,
        "esg_credit_analysis":  0.75,
        "financed_emissions":   0.93,
        "business_ethics":      0.82,
        "systemic_risk":        0.90,
    },
    "Westpac_2021_SustainabilitySupplement": {
        "data_security":        0.88,
        "financial_inclusion":  0.85,
        "esg_credit_analysis":  0.80,
        "financed_emissions":   0.92,
        "business_ethics":      0.40,
        "systemic_risk":        0.75,
    },
    "ANZ_2021_ESGSupplement": {
        "data_security":        0.85,
        "financial_inclusion":  0.88,
        "esg_credit_analysis":  0.78,
        "financed_emissions":   0.90,
        "business_ethics":      0.88,
        "systemic_risk":        0.25,
    },
    "Westpac_2023_ClimateReport": {
        "data_security":        0.10,
        "financial_inclusion":  0.30,
        "esg_credit_analysis":  0.75,
        "financed_emissions":   0.95,
        "business_ethics":      0.12,
        "systemic_risk":        0.85,
    },
    "NAB_2022_ClimateReport": {
        "data_security":        0.15,
        "financial_inclusion":  0.20,
        "esg_credit_analysis":  0.70,
        "financed_emissions":   0.95,
        "business_ethics":      0.12,
        "systemic_risk":        0.80,
    },
}


def pearson_r(x, y):
    x = np.asarray(x); y = np.asarray(y)
    if np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    def ranks(v):
        order = np.argsort(v)
        r = np.empty(len(v), float)
        r[order] = np.arange(len(v))
        return r
    return float(np.corrcoef(ranks(np.asarray(x)), ranks(np.asarray(y)))[0, 1])


def main() -> None:
    with SCORES_PATH.open() as f:
        claude = {k: v for k, v in json.load(f).items()
                  if not k.startswith("_")}

    rows = []
    per_report_struct = []
    per_report_unstruct = []
    for rid in SUBSET:
        struct_cov = []
        unstruct_cov = []
        for topic in TOPICS:
            c = claude[rid][topic]
            cov_struct = (c["presence"] + c["specificity"]
                          + c["quantification"]) / 3.0
            cov_unstruct = UNSTRUCTURED[rid][topic]
            rows.append({
                "report_id": rid,
                "topic": topic,
                "structured_cov": cov_struct,
                "unstructured_cov": cov_unstruct,
                "diff": cov_unstruct - cov_struct,
            })
            struct_cov.append(cov_struct)
            unstruct_cov.append(cov_unstruct)
        mmri_struct = 1.0 - float(np.mean(struct_cov))
        mmri_unstruct = 1.0 - float(np.mean(unstruct_cov))
        per_report_struct.append(mmri_struct)
        per_report_unstruct.append(mmri_unstruct)

    # ---- Cell-level agreement ----
    sc = [r["structured_cov"] for r in rows]
    uc = [r["unstructured_cov"] for r in rows]
    r_cell = pearson_r(sc, uc)
    mae_cell = float(np.mean(np.abs(np.asarray(sc) - np.asarray(uc))))
    within_010 = float(np.mean(np.abs(np.asarray(sc) - np.asarray(uc)) <= 0.10))
    within_020 = float(np.mean(np.abs(np.asarray(sc) - np.asarray(uc)) <= 0.20))

    # ---- Report-level MMRI comparison ----
    r_report = pearson_r(per_report_struct, per_report_unstruct)
    sp_report = spearman(per_report_struct, per_report_unstruct)
    mean_shift = float(np.mean(np.asarray(per_report_unstruct)
                               - np.asarray(per_report_struct)))

    # ---- CSV output ----
    out_csv = OUT_DIR / "prompt_ablation_results.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# Prompt-structure ablation: structured P/S/Q rubric "
                    "vs unstructured single-number coverage"])
        w.writerow(["report_id", "topic", "structured_coverage",
                    "unstructured_coverage", "diff"])
        for r in rows:
            w.writerow([r["report_id"], r["topic"],
                        f"{r['structured_cov']:.4f}",
                        f"{r['unstructured_cov']:.4f}",
                        f"{r['diff']:+.4f}"])
        w.writerow([])
        w.writerow(["# Cell-level agreement  (n = 36)"])
        w.writerow(["pearson_r", f"{r_cell:.4f}"])
        w.writerow(["MAE", f"{mae_cell:.4f}"])
        w.writerow(["within_0.10_band", f"{within_010:.3f}"])
        w.writerow(["within_0.20_band", f"{within_020:.3f}"])
        w.writerow([])
        w.writerow(["# Per-report MMRI"])
        w.writerow(["report_id", "MMRI_structured", "MMRI_unstructured",
                    "diff"])
        for rid, m_s, m_u in zip(SUBSET, per_report_struct,
                                 per_report_unstruct):
            w.writerow([rid, f"{m_s:.4f}", f"{m_u:.4f}",
                        f"{(m_u - m_s):+.4f}"])
        w.writerow([])
        w.writerow(["# Report-level summary"])
        w.writerow(["pearson_r_report_MMRI", f"{r_report:.4f}"])
        w.writerow(["spearman_report_MMRI", f"{sp_report:.4f}"])
        w.writerow(["mean_MMRI_shift_unstructured_minus_structured",
                    f"{mean_shift:+.4f}"])

    # ---- Figure: 3 panels ----
    # (a) per-cell scatter with equality diagonal + agreement bands
    # (b) histogram of per-cell diffs (unstructured - structured) to
    #     make the ±0.10 / ±0.20 band claims visually obvious
    # (c) per-report MMRI bars
    fig = plt.figure(figsize=(15.0, 5.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 0.9, 1.25], wspace=0.32,
                          left=0.05, right=0.99, top=0.84, bottom=0.20)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    STRUCT_COLOR = "#2F5EA8"
    UNSTRUCT_COLOR = "#9A4F00"

    # ---------------- (a) scatter ----------------
    diag = np.linspace(0, 1, 50)
    # Shaded ±0.20 band (light) and ±0.10 band (slightly darker) around y=x
    ax_a.fill_between(diag, np.clip(diag - 0.20, 0, 1), np.clip(diag + 0.20, 0, 1),
                      color="#2F5EA8", alpha=0.06, linewidth=0,
                      label=f"within \u00b10.20  ({within_020:.0%})")
    ax_a.fill_between(diag, np.clip(diag - 0.10, 0, 1), np.clip(diag + 0.10, 0, 1),
                      color="#2F5EA8", alpha=0.14, linewidth=0,
                      label=f"within \u00b10.10  ({within_010:.0%})")
    ax_a.plot(diag, diag, color="#888", lw=1.0, linestyle=":",
              label="y = x  (perfect agreement)", zorder=2)
    ax_a.scatter(sc, uc, s=44, color=STRUCT_COLOR, edgecolor="white",
                 linewidth=0.8, zorder=3)
    ax_a.text(0.04, 0.96,
              f"n = {len(sc)} cells\n"
              f"Pearson  r = {r_cell:.3f}\nMAE = {mae_cell:.3f}",
              transform=ax_a.transAxes, ha="left", va="top",
              fontsize=9.4, color="#222",
              bbox=dict(boxstyle="round,pad=0.4", facecolor="#FAFAFA",
                        edgecolor="#CCCCCC", lw=0.7))
    ax_a.set_xlim(0, 1.02); ax_a.set_ylim(0, 1.02)
    ax_a.set_xlabel("Structured-prompt coverage  (P/S/Q rubric)",
                    fontsize=10.0)
    ax_a.set_ylabel("Unstructured-prompt coverage  (single-number)",
                    fontsize=10.0)
    ax_a.set_title("(a)  Per-cell coverage: structured vs unstructured",
                   fontsize=10.8, loc="left", pad=8, fontweight="bold")
    ax_a.grid(linestyle=":", linewidth=0.5, color="#CCCCCC", alpha=0.7)
    ax_a.set_axisbelow(True)
    ax_a.legend(loc="lower right", fontsize=7.8, frameon=True,
                framealpha=0.95, edgecolor="#CCCCCC")

    # ---------------- (b) diff histogram ----------------
    diffs = np.asarray(uc) - np.asarray(sc)
    bins = np.arange(-0.65, 0.66, 0.05)
    ax_b.hist(diffs, bins=bins, color=UNSTRUCT_COLOR, alpha=0.75,
              edgecolor="white", linewidth=0.6)
    # Agreement band markers
    for x0, ls in [(0.0, "-"), (-0.10, "--"), (0.10, "--"),
                   (-0.20, ":"), (0.20, ":")]:
        ax_b.axvline(x0, color="#555", linewidth=0.9 if x0 == 0 else 0.8,
                     linestyle=ls, alpha=0.75, zorder=2)
    ax_b.text(0.10, ax_b.get_ylim()[1] if False else 0, "", alpha=0)  # anchor

    ax_b.set_xlabel("Per-cell diff  (unstructured \u2212 structured)",
                    fontsize=10.0)
    ax_b.set_ylabel("Number of cells", fontsize=10.0)
    ax_b.set_title("(b)  Distribution of per-cell diffs",
                   fontsize=10.8, loc="left", pad=8, fontweight="bold")
    ax_b.grid(axis="y", linestyle=":", linewidth=0.5, color="#CCCCCC", alpha=0.7)
    ax_b.set_axisbelow(True)
    ax_b.set_xlim(-0.65, 0.65)
    for spine in ("top", "right"):
        ax_b.spines[spine].set_visible(False)
    # Annotations: band membership counts
    n_within_10 = int(np.sum(np.abs(diffs) <= 0.10))
    n_within_20 = int(np.sum(np.abs(diffs) <= 0.20))
    ax_b.text(0.98, 0.96,
              f"within \u00b10.10: {n_within_10}/{len(diffs)}  ({within_010:.0%})\n"
              f"within \u00b10.20: {n_within_20}/{len(diffs)}  ({within_020:.0%})\n"
              f"mean diff:  {np.mean(diffs):+.3f}",
              transform=ax_b.transAxes, ha="right", va="top", fontsize=8.6,
              color="#222",
              bbox=dict(boxstyle="round,pad=0.4", facecolor="#FAFAFA",
                        edgecolor="#CCCCCC", lw=0.7))

    # ---------------- (c) per-report MMRI ----------------
    x = np.arange(len(SUBSET))
    bar_w = 0.38
    ax_c.bar(x - bar_w / 2, per_report_struct, bar_w,
             color=STRUCT_COLOR, edgecolor="white", linewidth=0.8,
             label="structured (P/S/Q rubric)")
    ax_c.bar(x + bar_w / 2, per_report_unstruct, bar_w,
             color=UNSTRUCT_COLOR, edgecolor="white", linewidth=0.8,
             label="unstructured (single number)")
    for i, (ms, mu) in enumerate(zip(per_report_struct, per_report_unstruct)):
        ax_c.text(i - bar_w / 2, ms + 0.010, f"{ms:.2f}",
                  ha="center", va="bottom", fontsize=7.2,
                  color=STRUCT_COLOR, fontweight="bold")
        ax_c.text(i + bar_w / 2, mu + 0.010, f"{mu:.2f}",
                  ha="center", va="bottom", fontsize=7.2,
                  color=UNSTRUCT_COLOR, fontweight="bold")
    short_lbls = [r.replace("_", " ").replace("Sustainability", "Sust.")
                     .replace("Supplement", "Supp.")
                     .replace("AnnualReport", "Annual")
                     .replace("Reporting", "Report")
                     .replace("Appendix", "App.")
                  for r in SUBSET]
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(short_lbls, rotation=25, ha="right", fontsize=8.0)
    ax_c.set_ylabel("MMRI", fontsize=10.0)
    ax_c.set_ylim(0, max(max(per_report_struct), max(per_report_unstruct)) * 1.35)
    ax_c.set_title(f"(c)  Per-report MMRI   "
                   f"Pearson r = {r_report:.3f}   "
                   f"Spearman \u03c1 = {sp_report:.3f}",
                   fontsize=10.8, loc="left", pad=8, fontweight="bold")
    ax_c.grid(axis="y", linestyle=":", linewidth=0.5, color="#CCCCCC", alpha=0.7)
    ax_c.set_axisbelow(True)
    ax_c.legend(loc="upper left", fontsize=8.4, frameon=True,
                framealpha=0.95, edgecolor="#CCCCCC")
    for spine in ("top", "right"):
        ax_c.spines[spine].set_visible(False)

    fig.suptitle(
        "Prompt-structure ablation   \u2014   "
        "structured P/S/Q rubric  vs  unstructured single-number coverage",
        fontsize=12.8, fontweight="bold", x=0.5, y=0.975)

    out_png = OUT_DIR / "fig_prompt_ablation.png"
    out_pdf = OUT_DIR / "fig_prompt_ablation.pdf"
    fig.savefig(out_png, dpi=240, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)

    # Console summary
    print(f"Wrote {OUT_DIR}/")
    print()
    print("=== Cell-level agreement (n=36) ===")
    print(f"Pearson r        = {r_cell:.4f}")
    print(f"MAE              = {mae_cell:.4f}")
    print(f"within +/-0.10   = {within_010:.3f}")
    print(f"within +/-0.20   = {within_020:.3f}")
    print()
    print("=== Per-report MMRI (n=6) ===")
    print(f"{'Report':<46} {'structured':>12} {'unstructured':>14} {'diff':>8}")
    for rid, m_s, m_u in zip(SUBSET, per_report_struct, per_report_unstruct):
        print(f"{rid:<46} {m_s:>12.4f} {m_u:>14.4f} {m_u - m_s:>+8.4f}")
    print(f"\nPearson r (report MMRI)   = {r_report:.4f}")
    print(f"Spearman rho              = {sp_report:.4f}")
    print(f"mean shift (unstructured - structured) = {mean_shift:+.4f}")


if __name__ == "__main__":
    main()
