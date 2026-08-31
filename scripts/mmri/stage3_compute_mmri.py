"""
Stage 3 — compute MMRI per report and render the paper figures.

PURPOSE
  Reads the LLM coverage scores from <results_dir>/coverage_scores.json,
  applies the applicability indicator a_i (climate-only reports skip non-climate topics),
  computes MMRI per report, writes the results table, and renders the three paper figures.

MMRI formula (paper Eq. 4):

    MMRI_r = ( sum_i  a_i * w_i * M_{r,i} ) / ( sum_i  a_i * w_i )

where
    M_{r,i} = 1 - C_{r,i}                        (per-topic misalignment)
    C_{r,i} = mean(Presence, Specificity, Quantification)
    a_i in {0, 1}                                (applicability indicator)
    w_i in [0, 1], sum_i w_i = 1                 (importance weight)

BASELINE WEIGHTS
  w_i = 1/6 for all six SASB FN-CB topics. a_i is 1 except for non-climate
  topics in climate-only reports (data_security, financial_inclusion,
  business_ethics are marked 0 for climate-only reports in the topic schema).

PIPELINE POSITION
  Runs AFTER stage2_score.py collect and is the final stage of the
  model-agnostic pipeline. Uses --results-dir to pick which model's
  scores to aggregate, same pattern as stage2_score.py.

INPUTS   <results_dir>/coverage_scores.json
OUTPUTS  <results_dir>/mmri_results.csv
         <results_dir>/fig1_heatmap.{png,pdf}
         <results_dir>/fig2_topic_bars.{png,pdf}
         <results_dir>/fig3_mmri_trend.{png,pdf}

Run:  python3 scripts/mmri/stage3_compute_mmri.py
      python3 scripts/mmri/stage3_compute_mmri.py --results-dir results/gpt
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Repository root, resolved relative to this file so the script runs from
# a clone at any location.
ROOT = Path(__file__).resolve().parent.parent.parent

# Default results directory is Claude. Override with --results-dir when
# running for another model (e.g. GPT). The script reads scores from
# <results_dir>/ and writes MMRI outputs alongside.
DEFAULT_RESULTS_DIR = ROOT / "results" / "claude"


def _init_paths(results_dir: Path) -> dict[str, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    return {
        "scores_json": results_dir / "coverage_scores.json",
        "out_dir": results_dir,
        "mmri_csv": results_dir / "mmri_results.csv",
    }

TOPICS = [
    "data_security",
    "financial_inclusion",
    "esg_credit_analysis",
    "financed_emissions",
    "business_ethics",
    "systemic_risk",
]
TOPIC_LABELS = {
    "data_security":       "Data\nSecurity",
    "financial_inclusion": "Financial\nInclusion",
    "esg_credit_analysis": "ESG in\nCredit",
    "financed_emissions":  "Financed\nEmissions",
    "business_ethics":     "Business\nEthics",
    "systemic_risk":       "Systemic\nRisk Mgmt",
}
BANKS = ["ANZ", "CBA", "NAB", "Westpac"]
YEARS = [2021, 2022, 2023, 2024, 2025]
BANK_COLOR = {"ANZ": "#0072CE", "CBA": "#E0A800", "NAB": "#1F968B", "Westpac": "#B22234"}
BANK_MARKER = {"ANZ": "o", "CBA": "s", "NAB": "D", "Westpac": "^"}
WEIGHT = 1.0 / len(TOPICS)


def parse_id(report_id: str) -> tuple[str, int]:
    m = re.match(r"([A-Za-z]+)_(\d{4})_", report_id)
    if not m:
        raise ValueError(report_id)
    return m.group(1), int(m.group(2))


def build_table(paths: dict[str, Path]) -> list[dict]:
    scores = json.load(paths["scores_json"].open())
    rows: list[dict] = []
    for rid, payload in scores.items():
        if rid.startswith("_"):
            continue
        bank, year = parse_id(rid)
        row: dict = {"report_id": rid, "bank": bank, "year": year}
        num = 0.0
        den = 0.0
        for t in TOPICS:
            cell = payload[t]
            c = (cell["presence"] + cell["specificity"] + cell["quantification"]) / 3.0
            m = 1.0 - c
            a = int(cell.get("a_i", 1))
            row[f"cov_{t}"] = round(c, 4)
            row[f"mis_{t}"] = round(m, 4)
            row[f"ai_{t}"] = a
            num += a * WEIGHT * m
            den += a * WEIGHT
        row["MMRI"] = round(num / den, 4) if den > 0 else 0.0
        row["n_topics_applicable"] = int(sum(row[f"ai_{t}"] for t in TOPICS))
        rows.append(row)
    rows.sort(key=lambda r: (r["bank"], r["year"]))
    return rows


def write_csv(rows: list[dict], paths: dict[str, Path]) -> None:
    fields = ["bank", "year", "report_id", "n_topics_applicable", "MMRI"] \
        + [f"cov_{t}" for t in TOPICS] + [f"ai_{t}" for t in TOPICS]
    with paths["mmri_csv"].open("w", newline="") as f:
        f.write("# Stage 3: MMRI per report, applying a_i (applicability) and w_i=1/6.\n")
        f.write("# MMRI_r = sum_i a_i w_i (1 - C_{r,i}) / sum_i a_i w_i\n")
        f.write("# C_{r,i} = mean(Presence, Specificity, Quantification); a_i=0 for non-climate topics in climate-only reports.\n")
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})
    print(f"Wrote {paths['mmri_csv']}")


def figure_heatmap(rows: list[dict], paths: dict[str, Path]) -> None:
    """Heatmap rows = (bank, year), columns = topics.

    Not-applicable cells (a_i = 0, non-climate topics in climate-only
    reports) are rendered as a flat neutral light-grey fill with no text
    and no hatching, and called out in a single legend swatch below the
    plot. This reads cleanly in print.
    """
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(11.8, 7.9))
    labels_y: list[str] = []
    grid = np.zeros((len(rows), len(TOPICS)))
    mask = np.zeros((len(rows), len(TOPICS)), dtype=bool)
    for i, r in enumerate(rows):
        labels_y.append(f"{r['bank']} {r['year']}")
        for j, t in enumerate(TOPICS):
            grid[i, j] = r[f"mis_{t}"]
            mask[i, j] = r[f"ai_{t}"] == 0

    # Paint a flat neutral light-grey behind NA cells first.
    NA_COLOR = "#ECECEC"
    na_layer = np.where(mask, 1.0, np.nan)
    ax.imshow(na_layer, aspect="auto",
              cmap=plt.matplotlib.colors.ListedColormap([NA_COLOR]),
              vmin=0, vmax=1)

    # Masked RdYlGn_r on top for the applicable cells only.
    im = ax.imshow(np.ma.array(grid, mask=mask), aspect="auto",
                   cmap="RdYlGn_r", vmin=0, vmax=1)

    ax.set_xticks(range(len(TOPICS)))
    ax.set_xticklabels([TOPIC_LABELS[t] for t in TOPICS], fontsize=10)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(labels_y, fontsize=9)
    ax.set_xlabel("SASB FN-CB materiality topic", fontsize=11)
    ax.set_title("Per-report materiality misalignment, Big Four AU banks (2021–2025)",
                 fontsize=12.5, pad=10)

    # Number labels only for applicable cells; NA cells stay blank.
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if mask[i, j]:
                continue
            v = grid[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=8, color=("white" if v > 0.6 or v < 0.2 else "black"))

    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.04)
    cbar.set_label("Misalignment $M_{r,i}=1-C_{r,i}$  (1 = no coverage, 0 = full coverage)",
                   fontsize=10, labelpad=10)
    cbar.ax.tick_params(labelsize=9)

    # Single legend swatch for NA cells, anchored below the plot.
    na_patch = mpatches.Patch(facecolor=NA_COLOR, edgecolor="#cccccc",
                              label="Topic not applicable (climate-only report)")
    ax.legend(handles=[na_patch], loc="upper center",
              bbox_to_anchor=(0.5, -0.10), frameon=False, fontsize=9)

    fig.subplots_adjust(left=0.14, right=0.88, top=0.91, bottom=0.14)
    out_png = paths["out_dir"] / "fig1_heatmap.png"
    out_pdf = paths["out_dir"] / "fig1_heatmap.pdf"
    fig.savefig(out_png, dpi=180, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png.name} / {out_pdf.name}")


def figure_topic_bars(rows: list[dict], paths: dict[str, Path]) -> None:
    """Mean misalignment per topic (only over applicable reports)."""
    fig, ax = plt.subplots(figsize=(11, 6))
    n = len(TOPICS); bar_w = 0.18; x = np.arange(n)
    data = {b: [0.0] * n for b in BANKS}
    counts = {b: [0] * n for b in BANKS}
    for r in rows:
        for j, t in enumerate(TOPICS):
            if r[f"ai_{t}"] == 1:
                data[r["bank"]][j] += r[f"mis_{t}"]
                counts[r["bank"]][j] += 1
    for b in BANKS:
        for j in range(n):
            if counts[b][j]:
                data[b][j] /= counts[b][j]

    for k, b in enumerate(BANKS):
        off = (k - 1.5) * bar_w
        bars = ax.bar(x + off, data[b], bar_w, label=b, color=BANK_COLOR[b],
                      edgecolor="white", linewidth=0.7)
        for bar, val in zip(bars, data[b]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                    f"{val:.2f}", ha="center", va="bottom",
                    fontsize=7.5, color=BANK_COLOR[b], fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([TOPIC_LABELS[t].replace("\n", " ") for t in TOPICS], fontsize=10)
    ax.set_ylabel("Mean misalignment $M_{r,i}$  (5-year avg, applicable reports only)", fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_title("Materiality misalignment by topic and bank (2021–2025)", fontsize=13, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.35); ax.set_axisbelow(True)
    ax.legend(loc="upper left", framealpha=0.95, fontsize=10, ncol=4)
    fig.tight_layout()
    out_png = paths["out_dir"] / "fig2_topic_bars.png"
    out_pdf = paths["out_dir"] / "fig2_topic_bars.pdf"
    fig.savefig(out_png, dpi=180, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png.name} / {out_pdf.name}")


def figure_trend(rows: list[dict], paths: dict[str, Path]) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.5))
    by_bank = {b: {} for b in BANKS}
    for r in rows:
        by_bank[r["bank"]][r["year"]] = r["MMRI"]
    for b in BANKS:
        ys = [by_bank[b][y] for y in YEARS]
        ax.plot(YEARS, ys, marker=BANK_MARKER[b], linewidth=2.2, markersize=10,
                label=b, color=BANK_COLOR[b], markeredgecolor="white", markeredgewidth=1.0)

    # Place each value label above or below its point, with extra spacing
    # whenever two banks are within 0.03 MMRI of each other in the same
    # year (common for CBA/NAB near-overlaps). The closer the neighbour,
    # the larger the vertical offset applied.
    PROXIMITY_THRESHOLD = 0.03
    BASE_OFFSET = 14       # default vertical offset in points
    EXTRA_OFFSET = 10      # added when a near-neighbour is detected
    for y in YEARS:
        items = sorted(((b, by_bank[b][y]) for b in BANKS), key=lambda x: x[1])
        n_ = len(items)
        for rank, (b, v) in enumerate(items):
            # Above/below alternating by rank
            sign = 1 if rank >= n_ / 2 else -1
            # Base magnitude grows with distance from the median rank
            mag = BASE_OFFSET + 6 * abs(rank - (n_ - 1) / 2)
            # If a neighbour in rank is within the proximity threshold,
            # fan this label further out to avoid overlap.
            neighbours = []
            if rank > 0:
                neighbours.append(items[rank - 1][1])
            if rank < n_ - 1:
                neighbours.append(items[rank + 1][1])
            if any(abs(v - nv) < PROXIMITY_THRESHOLD for nv in neighbours):
                mag += EXTRA_OFFSET
            dy = sign * mag
            va = "bottom" if sign > 0 else "top"
            ax.annotate(f"{v:.2f}", (y, v), textcoords="offset points",
                        xytext=(0, dy), ha="center", va=va,
                        fontsize=8.5, color=BANK_COLOR[b], fontweight="bold")

    ax.set_xlabel("Reporting year", fontsize=11)
    ax.set_ylabel("MMRI  (lower = better alignment)", fontsize=11)
    ax.set_xticks(YEARS)
    ax.set_ylim(-0.05, 0.7)
    ax.set_title("MMRI trend, Big Four AU banks (2021–2025)",
                 fontsize=13, pad=10)
    ax.grid(linestyle="--", alpha=0.35); ax.set_axisbelow(True)
    ax.legend(loc="upper right", framealpha=0.95, fontsize=10, ncol=4)
    ax.text(0.01, -0.13,
            r"MMRI$_r = \sum_i a_i w_i (1-C_{r,i}) / \sum_i a_i w_i$  with $w_i=1/6$; $a_i=0$ for non-climate topics in climate-only reports.",
            transform=ax.transAxes, fontsize=8.5, color="#444", ha="left")
    fig.tight_layout()
    out_png = paths["out_dir"] / "fig3_mmri_trend.png"
    out_pdf = paths["out_dir"] / "fig3_mmri_trend.pdf"
    fig.savefig(out_png, dpi=180, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png.name} / {out_pdf.name}")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
                    help=("directory containing stage2_results_scores/ "
                          "(default: Claude's)"))
    a = ap.parse_args()
    paths = _init_paths(a.results_dir)

    rows = build_table(paths)
    write_csv(rows, paths)
    print("\nSummary (MMRI per bank × year, applying a_i):")
    print(f"{'Bank':<8}", *[f"{y:<8}" for y in YEARS], "Δ(21→25)")
    for b in BANKS:
        ys = {r["year"]: r["MMRI"] for r in rows if r["bank"] == b}
        delta = ys[2025] - ys[2021]
        print(f"{b:<8}", *[f"{ys[y]:<8.3f}" for y in YEARS], f"{delta:+.3f}")
    figure_heatmap(rows, paths)
    figure_topic_bars(rows, paths)
    figure_trend(rows, paths)
    print("\nDone.")


if __name__ == "__main__":
    main()
