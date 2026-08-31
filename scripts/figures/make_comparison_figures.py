"""
Two-model comparison figures for the paper's "Comparison with the OpenAI
model" subsection.

WHAT THIS SCRIPT DOES
---------------------
Renders two paired small-multiples figures, both following the same
visual grammar as the Claude-only main figures:

  fig_mmri_by_bank_two_models      4 panels, one per bank
                                   x = year, y = MMRI, two lines per panel
                                   (Claude vs GPT-5.4-mini)

  fig_topic_coverage_by_year_two_models
                                   6 panels, one per SASB FN-CB topic
                                   x = year, y = mean coverage across banks
                                   two lines per panel (mean across the 4
                                   banks for each model), with shaded
                                   min-max ribbon showing per-bank spread

INPUTS   ../claude_results/stage2_results_scores/stage3_mmri_results.csv   (Claude)
         ../../GPT model expriements/stage2_results_scores/gpt_v2_mmri_results.csv  (GPT)
OUTPUTS  ./fig_mmri_by_bank_two_models.{png,pdf}
         ./fig_topic_coverage_by_year_two_models.{png,pdf}

Run:  python3 "Claude model experiment/two_model_comparison/make_comparison_figures.py"
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Repository root, resolved relative to this file so the script runs from
# a clone at any location.
ROOT = Path(__file__).resolve().parent.parent.parent
COMP_DIR = ROOT / "figures"
COMP_DIR.mkdir(parents=True, exist_ok=True)

CLAUDE_CSV = ROOT / "results" / "claude" / "mmri_results.csv"
GPT_CSV = ROOT / "results" / "gpt" / "mmri_results.csv"

BANKS = ["ANZ", "CBA", "NAB", "Westpac"]
YEARS = [2021, 2022, 2023, 2024, 2025]

# SASB FN-CB topics + display labels (kept short for panel titles)
TOPICS = [
    ("data_security", "Data security"),
    ("financial_inclusion", "Financial inclusion"),
    ("esg_credit_analysis", "ESG in credit"),
    ("financed_emissions", "Financed emissions"),
    ("business_ethics", "Business ethics"),
    ("systemic_risk", "Systemic risk"),
]

# Colour grammar: model identity dominates (blue = Claude, orange-brown = GPT).
# Per-bank distinction inside each panel comes from the panel title only,
# so the two lines are visually consistent across panels.
CLAUDE_COLOR = "#2F5EA8"
GPT_COLOR = "#9A4F00"


def load_table(path: Path) -> list[dict]:
    """Load a results table with both MMRI and per-topic coverage columns."""
    with path.open() as f:
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    rows: list[dict] = []
    for r in csv.DictReader(lines):
        rec = {
            "bank": r["bank"],
            "year": int(r["year"]),
            "report_id": r["report_id"],
            "MMRI": float(r["MMRI"]),
        }
        for col, _ in TOPICS:
            rec[f"cov_{col}"] = float(r[f"cov_{col}"])
        rows.append(rec)
    return rows


def pearson_r(x: list[float], y: list[float]) -> float:
    return float(np.corrcoef(np.asarray(x), np.asarray(y))[0, 1])


def make_figure() -> None:
    cl = load_table(CLAUDE_CSV)
    gp = load_table(GPT_CSV)
    cl_by = {(r["bank"], r["year"]): r["MMRI"] for r in cl}
    gp_by = {(r["bank"], r["year"]): r["MMRI"] for r in gp}

    # Headline stats for the figure footer
    cl_all = [cl_by[(b, y)] for b in BANKS for y in YEARS]
    gp_all = [gp_by[(b, y)] for b in BANKS for y in YEARS]
    r_val = pearson_r(cl_all, gp_all)
    mean_shift = float(np.mean(np.array(gp_all) - np.array(cl_all)))

    # Use per-bank y-ranges sized to the combined Claude+GPT range for that
    # bank, with small headroom for annotation labels above the top value.
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.8),
                             sharex=True, sharey=False)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.12,
                        hspace=0.32, wspace=0.22)

    BANK_YMAX = {"ANZ": 0.60, "CBA": 0.60, "NAB": 0.70, "Westpac": 0.80}
    for idx, bank in enumerate(BANKS):
        ax = axes[idx // 2][idx % 2]
        Y_MIN, Y_MAX = 0.0, BANK_YMAX[bank]
        cl_vals = [cl_by[(bank, y)] for y in YEARS]
        gp_vals = [gp_by[(bank, y)] for y in YEARS]

        ax.plot(YEARS, cl_vals, marker="o", color=CLAUDE_COLOR,
                lw=2.0, markersize=7, markeredgecolor="white",
                markeredgewidth=0.9, label="Claude (claude-opus-4-7)",
                zorder=3)
        ax.plot(YEARS, gp_vals, marker="s", color=GPT_COLOR,
                lw=2.0, markersize=7, markeredgecolor="white",
                markeredgewidth=0.9, label="GPT-5.4-mini",
                zorder=3)

        # Shade the gap between the two lines so the per-year shift is
        # visually obvious.
        ax.fill_between(YEARS, cl_vals, gp_vals,
                        color=GPT_COLOR, alpha=0.08, zorder=1)

        # Numeric labels. Default: Claude below its marker, GPT above its
        # marker, so the two labels never collide with each other and the
        # model-colour pairing with the marker is preserved. Edge cases:
        #   - if the Claude value is very low (< 0.10), lift its label ABOVE
        #     the marker so it doesn't fall on or below the x-axis.
        #   - if the GPT value is very high (within 0.08 of the panel y-max),
        #     drop its label BELOW the marker so it doesn't clip the top.
        gp_clip_threshold = Y_MAX - 0.08
        for y, v in zip(YEARS, cl_vals):
            dy = 9 if v < 0.10 else -13
            va = "bottom" if v < 0.10 else "top"
            ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points",
                        xytext=(0, dy), ha="center", va=va,
                        fontsize=7.6, color=CLAUDE_COLOR, fontweight="bold")
        for y, v in zip(YEARS, gp_vals):
            dy = -13 if v > gp_clip_threshold else 9
            va = "top" if v > gp_clip_threshold else "bottom"
            ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points",
                        xytext=(0, dy), ha="center", va=va,
                        fontsize=7.6, color=GPT_COLOR, fontweight="bold")

        # Per-bank mean shift in the panel's top-right corner
        bank_shift = float(np.mean(np.array(gp_vals) - np.array(cl_vals)))
        ax.text(0.98, 0.96, f"mean shift  +{bank_shift:.2f}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8.6, color="#444",
                bbox=dict(boxstyle="round,pad=0.30", facecolor="#FAFAFA",
                          edgecolor="#CCCCCC", lw=0.7))

        ax.set_title(bank, fontsize=12.0, fontweight="bold", loc="left",
                     pad=6, color="#222")
        ax.set_xticks(YEARS)
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.grid(linestyle=":", linewidth=0.5, color="#CCCCCC", alpha=0.7)
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    # Outer axis labels
    fig.text(0.5, 0.07, "Reporting year",
             ha="center", va="center", fontsize=10.6)
    fig.text(0.015, 0.50, "MMRI  (lower = better disclosure alignment)",
             ha="center", va="center", rotation=90, fontsize=10.6)

    # Single legend at the figure top, two entries
    handles = [
        plt.Line2D([], [], color=CLAUDE_COLOR, marker="o", lw=2.0,
                   markersize=8, markeredgecolor="white",
                   markeredgewidth=0.9, label="Claude  (claude-opus-4-7)"),
        plt.Line2D([], [], color=GPT_COLOR, marker="s", lw=2.0,
                   markersize=8, markeredgecolor="white",
                   markeredgewidth=0.9, label="GPT-5.4-mini"),
    ]
    # Legend lifted above the panel titles so it never covers "ANZ" / "CBA".
    fig.legend(handles=handles, loc="upper center",
               bbox_to_anchor=(0.5, 0.92), ncol=2,
               fontsize=10.6, frameon=True, framealpha=0.95,
               edgecolor="#CCCCCC")

    fig.suptitle(
        "MMRI per bank under two LLM scorers   (2021 \u2013 2025)",
        fontsize=13.4, fontweight="bold", x=0.5, y=0.985)

    # Footer with the headline statistics
    fig.text(0.5, 0.02,
             f"n = 20 reports   \u00b7   "
             f"Pearson  r = {r_val:.3f}   \u00b7   "
             f"mean MMRI shift  =  +{mean_shift:.3f}",
             ha="center", va="bottom", fontsize=9.2, color="#555",
             style="italic")

    out_png = COMP_DIR / "fig_mmri_by_bank_two_models.png"
    out_pdf = COMP_DIR / "fig_mmri_by_bank_two_models.pdf"
    fig.savefig(out_png, dpi=240, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png.name} / {out_pdf.name}")
    print(f"   n = 20    Pearson r = {r_val:.3f}    "
          f"mean shift = +{mean_shift:.3f}")
    print("   Per-bank shifts:")
    for b in BANKS:
        cls = [cl_by[(b, y)] for y in YEARS]
        gps = [gp_by[(b, y)] for y in YEARS]
        print(f"     {b:8s}  +{float(np.mean(np.array(gps)-np.array(cls))):.3f}")


def make_topic_figure() -> None:
    """6-panel topic comparison: per-topic coverage trend over years, both
    models. Each panel shows the mean across the 4 banks with a shaded
    min-max ribbon to indicate per-bank spread."""
    cl = load_table(CLAUDE_CSV)
    gp = load_table(GPT_CSV)

    # Build (model, topic, year) -> list of bank coverages
    def by_model(rows, col):
        out = {y: [] for y in YEARS}
        for r in rows:
            out[r["year"]].append(r[col])
        return out  # year -> [4 bank coverages]

    fig, axes = plt.subplots(2, 3, figsize=(13.0, 7.4),
                             sharex=True, sharey=True)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.13,
                        hspace=0.32, wspace=0.16)

    # Bump y-max above 1.0 so Claude (above-marker) labels for high-value
    # topics like financed emissions (~0.97) have headroom and don't get
    # clipped at the panel ceiling.
    Y_MIN, Y_MAX = 0.0, 1.10
    for idx, (col, title) in enumerate(TOPICS):
        ax = axes[idx // 3][idx % 3]
        cl_by_year = by_model(cl, f"cov_{col}")
        gp_by_year = by_model(gp, f"cov_{col}")

        cl_mean = [float(np.mean(cl_by_year[y])) for y in YEARS]
        gp_mean = [float(np.mean(gp_by_year[y])) for y in YEARS]
        cl_min = [float(np.min(cl_by_year[y])) for y in YEARS]
        cl_max = [float(np.max(cl_by_year[y])) for y in YEARS]
        gp_min = [float(np.min(gp_by_year[y])) for y in YEARS]
        gp_max = [float(np.max(gp_by_year[y])) for y in YEARS]

        # min-max ribbons (light) — per-bank spread for each model
        ax.fill_between(YEARS, cl_min, cl_max,
                        color=CLAUDE_COLOR, alpha=0.12, zorder=1,
                        linewidth=0)
        ax.fill_between(YEARS, gp_min, gp_max,
                        color=GPT_COLOR, alpha=0.12, zorder=1,
                        linewidth=0)

        # mean lines (bold) — what the reader's eye should follow
        ax.plot(YEARS, cl_mean, marker="o", color=CLAUDE_COLOR,
                lw=2.0, markersize=6.5, markeredgecolor="white",
                markeredgewidth=0.9, zorder=4)
        ax.plot(YEARS, gp_mean, marker="s", color=GPT_COLOR,
                lw=2.0, markersize=6.5, markeredgecolor="white",
                markeredgewidth=0.9, zorder=4)

        # Numeric mean values: default rule is Claude (blue) ABOVE, GPT
        # (red) BELOW. This works because Claude scores higher than GPT
        # in 5 of 6 topics. The local exception is years where GPT
        # actually exceeds Claude (e.g. business ethics 2021): for those
        # years we FLIP the two labels (GPT above, Claude below) so
        # neither label is sandwiched between the other model's marker
        # and label.
        for y, c_val, g_val in zip(YEARS, cl_mean, gp_mean):
            if g_val >= c_val:
                # GPT is on top -> GPT above, Claude below
                ax.annotate(f"{g_val:.2f}", (y, g_val),
                            textcoords="offset points", xytext=(0, 9),
                            ha="center", va="bottom", fontsize=7.2,
                            color=GPT_COLOR, fontweight="bold")
                ax.annotate(f"{c_val:.2f}", (y, c_val),
                            textcoords="offset points", xytext=(0, -13),
                            ha="center", va="top", fontsize=7.2,
                            color=CLAUDE_COLOR, fontweight="bold")
            else:
                # Default (Claude on top) -> Claude above, GPT below
                ax.annotate(f"{c_val:.2f}", (y, c_val),
                            textcoords="offset points", xytext=(0, 9),
                            ha="center", va="bottom", fontsize=7.2,
                            color=CLAUDE_COLOR, fontweight="bold")
                ax.annotate(f"{g_val:.2f}", (y, g_val),
                            textcoords="offset points", xytext=(0, -13),
                            ha="center", va="top", fontsize=7.2,
                            color=GPT_COLOR, fontweight="bold")

        # per-topic mean shift — pinned to the panel BOTTOM-RIGHT corner so
        # it never competes with the Claude (above-marker) numeric labels.
        topic_shift = float(np.mean(np.array(gp_mean) - np.array(cl_mean)))
        sign = "+" if topic_shift >= 0 else "−"
        ax.text(0.98, 0.04,
                f"shift  {sign}{abs(topic_shift):.2f}",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8.4, color="#444",
                bbox=dict(boxstyle="round,pad=0.30", facecolor="#FAFAFA",
                          edgecolor="#CCCCCC", lw=0.7))

        ax.set_title(title, fontsize=11.6, fontweight="bold", loc="left",
                     pad=6, color="#222")
        ax.set_xticks(YEARS)
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.grid(linestyle=":", linewidth=0.5, color="#CCCCCC", alpha=0.7)
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    # outer axis labels
    fig.text(0.5, 0.07, "Reporting year",
             ha="center", va="center", fontsize=10.6)
    fig.text(0.012, 0.50,
             "mean coverage  $C_{r,i}$  (higher = stronger disclosure)",
             ha="center", va="center", rotation=90, fontsize=10.6)

    # legend at the top
    handles = [
        plt.Line2D([], [], color=CLAUDE_COLOR, marker="o", lw=2.0,
                   markersize=8, markeredgecolor="white",
                   markeredgewidth=0.9,
                   label="Claude (claude-opus-4-7)  \u2014  mean across banks"),
        plt.Line2D([], [], color=GPT_COLOR, marker="s", lw=2.0,
                   markersize=8, markeredgecolor="white",
                   markeredgewidth=0.9,
                   label="GPT-5.4-mini  \u2014  mean across banks"),
        plt.Rectangle((0, 0), 1, 1, facecolor="#888888", alpha=0.18,
                      edgecolor="none",
                      label="shaded ribbon = per-bank min/max range"),
    ]
    fig.legend(handles=handles, loc="upper center",
               bbox_to_anchor=(0.5, 0.94), ncol=3,
               fontsize=9.6, frameon=True, framealpha=0.95,
               edgecolor="#CCCCCC")

    fig.suptitle(
        "Topic-level coverage per year under two LLM scorers   "
        "(2021 \u2013 2025,  6 SASB FN-CB topics)",
        fontsize=13.2, fontweight="bold", x=0.5, y=0.99)

    out_png = COMP_DIR / "fig_topic_coverage_by_year_two_models.png"
    out_pdf = COMP_DIR / "fig_topic_coverage_by_year_two_models.pdf"
    fig.savefig(out_png, dpi=240, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png.name} / {out_pdf.name}")
    print("   Per-topic mean shifts (GPT \u2212 Claude, averaged over years):")
    for col, title in TOPICS:
        cl_y = [float(np.mean([r[f"cov_{col}"] for r in cl
                              if r["year"] == y])) for y in YEARS]
        gp_y = [float(np.mean([r[f"cov_{col}"] for r in gp
                              if r["year"] == y])) for y in YEARS]
        d = float(np.mean(np.array(gp_y) - np.array(cl_y)))
        sign = "+" if d >= 0 else "−"
        print(f"     {title:<22s}  {sign}{abs(d):.3f}")


if __name__ == "__main__":
    make_figure()
    make_topic_figure()
