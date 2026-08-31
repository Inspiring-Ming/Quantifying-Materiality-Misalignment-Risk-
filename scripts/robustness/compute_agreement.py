"""
Human-validation agreement metrics (CSV workflow).

WHAT THIS SCRIPT DOES
---------------------
Reads the filled annotations_filled.csv, joins annotator P/S/Q scores
with the Claude scores from the main-study JSON, and computes:

  - Per-dimension Pearson r  (annotator vs Claude on P, S, Q, and on
    combined coverage C = (P+S+Q)/3)
  - Per-dimension mean absolute error (MAE)
  - Cell-level agreement bands: % of cells where |annotator C - Claude C|
    is within 0.10 / 0.20 / 0.30
  - Cohen's kappa on binarised Presence (>=0.5 vs <0.5)

INPUTS   ./annotations_filled.csv                         (filled by annotator)
         ../../claude_results/stage2_results_scores/stage2_llm_coverage_scores.json (Claude main-study scores)

OUTPUTS  ./annotations.csv            (normalised annotator scores joined with Claude)
         ./agreement_metrics.csv      (summary metrics)
         ./fig_agreement.{png,pdf}    (annotator vs Claude scatter + per-dimension bars)

Run:  python3 "Claude model experiment/ablation_and_variance/human_validation/compute_agreement.py"
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REF_DIR = Path(__file__).resolve().parent
ROOT = REF_DIR.parents[2]
ANNOT_CSV = REF_DIR / "annotations_filled.csv"
CLAUDE_SCORES = ROOT / "results" / "claude" / "coverage_scores.json"

ALLOWED = {0.0, 0.25, 0.5, 0.75, 1.0}


# ============================================================
# CSV parsing + QC
# ============================================================
def parse_csv() -> list[dict]:
    if not ANNOT_CSV.exists():
        raise FileNotFoundError(
            f"annotations_filled.csv not found at {ANNOT_CSV}. "
            "Run build_csv_template.py first."
        )
    cells: list[dict] = []
    with ANNOT_CSV.open() as f:
        for r in csv.DictReader(f):
            cells.append(r)
    return cells


def _parse_score(raw: str, cell_idx: str, dim: str) -> float | None:
    s = (raw or "").strip()
    if s == "":
        return None
    try:
        v = float(s)
    except ValueError:
        raise SystemExit(
            f"Cell {cell_idx} {dim}: value '{raw}' is not a number. "
            f"Use one of 0, 0.25, 0.5, 0.75, 1."
        )
    if v not in ALLOWED:
        raise SystemExit(
            f"Cell {cell_idx} {dim}: value {v} is not one of the allowed "
            f"anchors {sorted(ALLOWED)}."
        )
    return v


def check_completeness(cells: list[dict]) -> list[dict]:
    """Validate and normalise; exit if anything is missing or malformed."""
    unfilled: list[str] = []
    normalised: list[dict] = []
    for c in cells:
        idx = c.get("cell_idx", "?")
        p = _parse_score(c.get("P", ""), idx, "P")
        s = _parse_score(c.get("S", ""), idx, "S")
        q = _parse_score(c.get("Q", ""), idx, "Q")
        if p is None or s is None or q is None:
            unfilled.append(f"  cell {idx:>2}  {c.get('report_id','?')} / {c.get('topic','?')}")
            continue
        normalised.append({
            "cell_idx": int(idx),
            "report_id": c["report_id"],
            "topic": c["topic"],
            "P": p, "S": s, "Q": q,
            "notes": c.get("notes", "").strip(),
        })

    if unfilled:
        print(f"WARNING: {len(unfilled)} cell(s) have empty P/S/Q values:")
        for u in unfilled:
            print(u)
        print()
        print("Fill the P, S, Q columns in annotations_filled.csv and re-run.")
        print("Refusing to compute partial agreement metrics.")
        raise SystemExit(1)

    return normalised


# ============================================================
# Agreement metrics
# ============================================================
def pearson_r(x: list[float], y: list[float]) -> float:
    x = np.asarray(x); y = np.asarray(y)
    if np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def mae(x: list[float], y: list[float]) -> float:
    return float(np.mean(np.abs(np.asarray(x) - np.asarray(y))))


def cohens_kappa_binary(x: list[float], y: list[float],
                        threshold: float = 0.5) -> float:
    xb = np.asarray([1 if v >= threshold else 0 for v in x])
    yb = np.asarray([1 if v >= threshold else 0 for v in y])
    po = float(np.mean(xb == yb))
    p_x1 = float(np.mean(xb))
    p_y1 = float(np.mean(yb))
    pe = p_x1 * p_y1 + (1 - p_x1) * (1 - p_y1)
    if pe == 1.0:
        return float("nan")
    return (po - pe) / (1 - pe)


def within_band(x: list[float], y: list[float], band: float) -> float:
    diffs = np.abs(np.asarray(x) - np.asarray(y))
    return float(np.mean(diffs <= band))


# ============================================================
# Main
# ============================================================
def main() -> None:
    raw = parse_csv()
    cells = check_completeness(raw)
    print(f"Loaded {len(cells)} annotated cells.")

    with CLAUDE_SCORES.open() as f:
        claude = {k: v for k, v in json.load(f).items()
                  if not k.startswith("_")}

    rows = []
    for c in cells:
        rid, topic = c["report_id"], c["topic"]
        if rid not in claude or topic not in claude[rid]:
            print(f"ERROR: Claude scores not found for {rid} / {topic}")
            continue
        cs = claude[rid][topic]
        hu_P, hu_S, hu_Q = c["P"], c["S"], c["Q"]
        hu_C = (hu_P + hu_S + hu_Q) / 3.0
        cl_P, cl_S, cl_Q = cs["presence"], cs["specificity"], cs["quantification"]
        cl_C = (cl_P + cl_S + cl_Q) / 3.0
        rows.append({
            "cell_idx": c["cell_idx"],
            "report_id": rid,
            "topic": topic,
            "hu_P": hu_P, "hu_S": hu_S, "hu_Q": hu_Q, "hu_C": hu_C,
            "cl_P": cl_P, "cl_S": cl_S, "cl_Q": cl_Q, "cl_C": cl_C,
            "diff_C": hu_C - cl_C,
            "notes": c["notes"],
            "uncertain": c["notes"].strip().upper().startswith("UNCERTAIN"),
        })

    out_annot = REF_DIR / "annotations.csv"
    with out_annot.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "# Human-validation reference set: annotator scores joined with Claude scores"
        ])
        w.writerow(["cell_idx", "report_id", "topic",
                    "hu_P", "hu_S", "hu_Q", "hu_C",
                    "cl_P", "cl_S", "cl_Q", "cl_C",
                    "diff_coverage", "uncertain", "notes"])
        for r in rows:
            w.writerow([r["cell_idx"], r["report_id"], r["topic"],
                        r["hu_P"], r["hu_S"], r["hu_Q"], f"{r['hu_C']:.4f}",
                        r["cl_P"], r["cl_S"], r["cl_Q"], f"{r['cl_C']:.4f}",
                        f"{r['diff_C']:+.4f}", int(r["uncertain"]), r["notes"]])

    hu_P = [r["hu_P"] for r in rows]; cl_P = [r["cl_P"] for r in rows]
    hu_S = [r["hu_S"] for r in rows]; cl_S = [r["cl_S"] for r in rows]
    hu_Q = [r["hu_Q"] for r in rows]; cl_Q = [r["cl_Q"] for r in rows]
    hu_C = [r["hu_C"] for r in rows]; cl_C = [r["cl_C"] for r in rows]

    metrics = []
    for name, hu, cl in [
        ("Presence", hu_P, cl_P),
        ("Specificity", hu_S, cl_S),
        ("Quantification", hu_Q, cl_Q),
        ("Coverage (combined)", hu_C, cl_C),
    ]:
        metrics.append({
            "dimension": name,
            "pearson_r": pearson_r(hu, cl),
            "mae": mae(hu, cl),
            "within_0.10": within_band(hu, cl, 0.10),
            "within_0.20": within_band(hu, cl, 0.20),
            "within_0.30": within_band(hu, cl, 0.30),
        })

    kappa_P = cohens_kappa_binary(hu_P, cl_P)

    out_metrics = REF_DIR / "agreement_metrics.csv"
    with out_metrics.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "# Agreement between single human annotator and Claude "
            "(claude-opus-4-7) on 30 (report, topic) cells"
        ])
        w.writerow(["dimension", "pearson_r", "MAE",
                    "within_0.10_band", "within_0.20_band",
                    "within_0.30_band"])
        for m in metrics:
            w.writerow([m["dimension"],
                        f"{m['pearson_r']:.4f}",
                        f"{m['mae']:.4f}",
                        f"{m['within_0.10']:.3f}",
                        f"{m['within_0.20']:.3f}",
                        f"{m['within_0.30']:.3f}"])
        w.writerow([])
        w.writerow(["# Cohen's kappa on binarised Presence (threshold = 0.5)"])
        w.writerow(["kappa_presence_binarised", f"{kappa_P:.4f}"])
        n_unc = sum(1 for r in rows if r["uncertain"])
        w.writerow([])
        w.writerow(["# Cells flagged UNCERTAIN by annotator"])
        w.writerow([f"{n_unc}/{len(rows)}"])

        # Per-topic breakdown: n, mean-shift, MAE on each dimension
        TOPIC_ORDER = [
            "data_security", "financial_inclusion", "esg_credit_analysis",
            "financed_emissions", "business_ethics", "systemic_risk",
        ]
        topic_stats = {}
        for t in TOPIC_ORDER:
            trows = [r for r in rows if r["topic"] == t]
            if not trows:
                continue
            hP = [r["hu_P"] for r in trows]; cP = [r["cl_P"] for r in trows]
            hS = [r["hu_S"] for r in trows]; cS = [r["cl_S"] for r in trows]
            hQ = [r["hu_Q"] for r in trows]; cQ = [r["cl_Q"] for r in trows]
            hC = [r["hu_C"] for r in trows]; cC = [r["cl_C"] for r in trows]
            topic_stats[t] = {
                "n": len(trows),
                "mean_diff_C": float(np.mean(np.asarray(hC) - np.asarray(cC))),
                "mae_P": mae(hP, cP), "mae_S": mae(hS, cS),
                "mae_Q": mae(hQ, cQ), "mae_C": mae(hC, cC),
            }
        w.writerow([])
        w.writerow(["# Per-topic breakdown (human - Claude)"])
        w.writerow(["topic", "n", "mean_diff_coverage",
                    "MAE_P", "MAE_S", "MAE_Q", "MAE_coverage"])
        for t, s in topic_stats.items():
            w.writerow([t, s["n"], f"{s['mean_diff_C']:+.4f}",
                        f"{s['mae_P']:.4f}", f"{s['mae_S']:.4f}",
                        f"{s['mae_Q']:.4f}", f"{s['mae_C']:.4f}"])

    # ---- Unified 3-panel figure ----
    TOPIC_DISPLAY = {
        "data_security":       "Data security",
        "financial_inclusion": "Financial inclusion",
        "esg_credit_analysis": "ESG in credit",
        "financed_emissions":  "Financed emissions",
        "business_ethics":     "Business ethics",
        "systemic_risk":       "Systemic risk",
    }
    # Sort topics by mean shift (most negative first) so panels (b) and
    # (c) share the same top-to-bottom ordering.
    sorted_topics = sorted(topic_stats.keys(),
                           key=lambda t: topic_stats[t]["mean_diff_C"])

    fig = plt.figure(figsize=(16.8, 5.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.25, 1.05],
                          wspace=0.42, left=0.055, right=0.985,
                          top=0.84, bottom=0.22)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])

    # ---- Panel (a): per-cell scatter, confident vs UNCERTAIN ----
    diag = np.linspace(0, 1, 50)
    ax_a.plot(diag, diag, color="#BBBBBB", lw=1.0, linestyle=":",
              label="equal scores (above: human higher)", zorder=1)

    conf_rows = [r for r in rows if not r["uncertain"]]
    unc_rows = [r for r in rows if r["uncertain"]]
    if conf_rows:
        ax_a.scatter([r["cl_C"] for r in conf_rows],
                     [r["hu_C"] for r in conf_rows],
                     s=58, color="#2F5EA8", edgecolor="white",
                     linewidth=0.8, zorder=3, label="confident")
    if unc_rows:
        ax_a.scatter([r["cl_C"] for r in unc_rows],
                     [r["hu_C"] for r in unc_rows],
                     s=70, facecolor="none", edgecolor="#B22234",
                     linewidth=1.6, zorder=4, label="annotator uncertain")

    r_val = pearson_r(hu_C, cl_C)
    mae_val = mae(hu_C, cl_C)
    mean_shift = float(np.mean(np.asarray(hu_C) - np.asarray(cl_C)))

    # Stats box in the top-left corner where there is no data.
    ax_a.text(0.04, 0.96,
              f"Pearson  r = {r_val:.2f}\n"
              f"mean shift = {mean_shift:+.2f}\n"
              f"n = {len(rows)} cells",
              transform=ax_a.transAxes, ha="left", va="top",
              fontsize=9.4, color="#222",
              bbox=dict(boxstyle="round,pad=0.4", facecolor="#FAFAFA",
                        edgecolor="#CCCCCC", lw=0.7))
    ax_a.set_xlim(0, 1.02); ax_a.set_ylim(0, 1.02)
    ax_a.set_xlabel("Claude coverage score", fontsize=10.6)
    ax_a.set_ylabel("Human coverage score", fontsize=10.6)
    ax_a.set_title("(a)  Cell-level agreement",
                   fontsize=11.4, loc="left", pad=8, fontweight="bold")
    ax_a.grid(linestyle=":", linewidth=0.5, color="#CCCCCC", alpha=0.7)
    ax_a.set_axisbelow(True)
    ax_a.legend(loc="lower right", fontsize=8.4, frameon=True,
                framealpha=0.95, edgecolor="#CCCCCC")

    # ---- Panel (b): per-topic mean shift, horizontal bars ----
    shifts = [topic_stats[t]["mean_diff_C"] for t in sorted_topics]
    labels = [TOPIC_DISPLAY[t] for t in sorted_topics]
    ns = [topic_stats[t]["n"] for t in sorted_topics]

    def _shift_color(v: float) -> str:
        # red for |shift| > 0.30, orange for 0.10-0.30, grey for |shift| <= 0.10
        a = abs(v)
        if a > 0.30:
            return "#B22234"
        if a > 0.10:
            return "#9A4F00"
        return "#888888"

    bar_colors = [_shift_color(v) for v in shifts]
    y_pos = np.arange(len(sorted_topics))
    ax_b.barh(y_pos, shifts, color=bar_colors,
              edgecolor="white", linewidth=0.8)
    ax_b.axvline(0, color="#333333", lw=0.8)
    for y, v, n in zip(y_pos, shifts, ns):
        ha = "left" if v >= 0 else "right"
        x_text = v + (0.015 if v >= 0 else -0.015)
        ax_b.text(x_text, y, f"{v:+.2f}",
                  va="center", ha=ha, fontsize=9.2, color="#222",
                  fontweight="bold")
    ax_b.set_yticks(y_pos)
    ax_b.set_yticklabels(labels, fontsize=9.8)
    ax_b.invert_yaxis()
    xmax = max(0.05, max(abs(v) for v in shifts) * 1.55)
    ax_b.set_xlim(-xmax, xmax)
    ax_b.set_xlabel("Human score  \u2212  Claude score", fontsize=10.6)

    # Direction hints below the axis label so they never overlap bars.
    # Placed in figure-coord space via the axes transform at y < 0.
    ax_b.annotate("\u2190 Claude scored higher", xy=(0, -0.20),
                  xycoords="axes fraction", ha="left", va="top",
                  fontsize=8.6, color="#666", style="italic")
    ax_b.annotate("Human scored higher \u2192", xy=(1, -0.20),
                  xycoords="axes fraction", ha="right", va="top",
                  fontsize=8.6, color="#666", style="italic")

    ax_b.set_title("(b)  Disagreement by topic",
                   fontsize=11.4, loc="left", pad=8, fontweight="bold")
    ax_b.grid(axis="x", linestyle=":", linewidth=0.5, color="#CCCCCC",
              alpha=0.7)
    ax_b.set_axisbelow(True)
    for spine in ("top", "right"):
        ax_b.spines[spine].set_visible(False)

    # ---- Panel (c): per-topic x per-dimension MAE heatmap ----
    dim_keys = ["mae_P", "mae_S", "mae_Q"]
    dim_labels = ["Presence", "Specificity", "Quantification"]
    H = np.array([[topic_stats[t][k] for k in dim_keys]
                  for t in sorted_topics])
    im = ax_c.imshow(H, cmap="Reds", vmin=0.0, vmax=0.75, aspect="auto")
    ax_c.set_xticks(range(len(dim_labels)))
    ax_c.set_xticklabels(dim_labels, fontsize=9.8)
    ax_c.set_yticks(range(len(sorted_topics)))
    ax_c.set_yticklabels(labels, fontsize=9.8)
    for i in range(len(sorted_topics)):
        for j in range(len(dim_labels)):
            v = H[i, j]
            txt_color = "white" if v > 0.40 else "#222"
            ax_c.text(j, i, f"{v:.2f}", ha="center", va="center",
                      fontsize=9.4, color=txt_color, fontweight="bold")
    ax_c.set_title("(c)  Disagreement by scoring dimension",
                   fontsize=11.4, loc="left", pad=8, fontweight="bold")
    cb = fig.colorbar(im, ax=ax_c, fraction=0.046, pad=0.04)
    cb.set_label("Average gap between human and Claude", fontsize=9.4)
    cb.ax.tick_params(labelsize=8.4)

    fig.suptitle(
        "Human vs Claude scoring on 30 cells "
        "\u2014 where they agree, where they don't",
        fontsize=13.0, fontweight="bold", x=0.5, y=0.965)

    out_png = REF_DIR / "fig_human_validation.png"
    out_pdf = REF_DIR / "fig_human_validation.pdf"
    fig.savefig(out_png, dpi=240, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)

    # Retire the old separate figures if they exist (we now have one
    # unified figure for the paper).
    for stale in ("fig_agreement.png", "fig_agreement.pdf",
                  "fig_agreement_by_topic.png", "fig_agreement_by_topic.pdf"):
        stale_path = REF_DIR / stale
        if stale_path.exists():
            stale_path.unlink()

    print(f"\nWrote  {out_annot.name}")
    print(f"Wrote  {out_metrics.name}")
    print(f"Wrote  {out_png.name} / {out_pdf.name}")
    print()
    pm = "\u00b1"
    print(f"{'dimension':<22} {'Pearson r':>10} {'MAE':>8} "
          f"{pm + '0.10':>8} {pm + '0.20':>8} {pm + '0.30':>8}")
    for m in metrics:
        print(f"{m['dimension']:<22} {m['pearson_r']:>10.3f} "
              f"{m['mae']:>8.3f} {m['within_0.10']:>8.3f} "
              f"{m['within_0.20']:>8.3f} {m['within_0.30']:>8.3f}")
    print()
    print(f"Cohen's kappa (binarised Presence >= 0.5): {kappa_P:.3f}")
    uncertain = sum(1 for r in rows if r["uncertain"])
    print(f"Cells flagged UNCERTAIN: {uncertain}/{len(rows)}")

    print()
    print(f"{'topic':<22} {'n':>3} {'meanDiff':>10} "
          f"{'MAE_P':>7} {'MAE_S':>7} {'MAE_Q':>7} {'MAE_C':>7}")
    for t in sorted_topics:
        s = topic_stats[t]
        print(f"{TOPIC_DISPLAY[t]:<22} {s['n']:>3} "
              f"{s['mean_diff_C']:>+10.3f} "
              f"{s['mae_P']:>7.3f} {s['mae_S']:>7.3f} "
              f"{s['mae_Q']:>7.3f} {s['mae_C']:>7.3f}")


if __name__ == "__main__":
    main()