"""
Banking instantiation of the framework — Figure 2 of the paper.

WHAT THIS SCRIPT DOES
---------------------
Renders Figure 2: the commercial-banking instantiation of the generic
three-layer framework. Layer A uses the six SASB FN-CB materiality topics,
Layer B describes our actual pipeline (pdfplumber + retrieval + Claude/Gemini
LLM scoring), Layer C points to the three concrete results figures we
produce in this folder.

Pair with: make_framework_generic_figure.py  (Figure 1, industry-agnostic).

INPUTS   none (self-contained)
OUTPUTS  ./framework_banking.{png,pdf}   (Elsevier two-column-friendly)

Run:  python3 results/make_framework_banking_figure.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# Repository root, resolved relative to this file.
ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIG_W, FIG_H = 13.0, 9.0
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")

# ---------- palette ----------
BAND_A = "#EEF3FA"
BAND_B = "#F7F2EA"
BAND_C = "#EEF4EF"
E_A = "#2F5EA8"   # blue
E_B = "#8A5A2B"   # brown
E_C = "#2E7D4F"   # green
E_MMRI = "#6B2E8C"  # purple
E_VAL = "#9A7A0A"   # gold
WHITE = "#FFFFFF"
C_MMRI_FILL = "#F3EAF7"
C_VAL_FILL = "#FFF6D6"
DARK = "#141414"
MUTED = "#606060"


def band(y, h, face, label, edge):
    ax.add_patch(Rectangle((0.20, y), FIG_W - 0.40, h,
                           facecolor=face, edgecolor="none", zorder=0))
    ax.text(0.38, y + h - 0.20, label,
            ha="left", va="top", fontsize=10.4, fontweight="bold",
            color=edge, style="italic")


def box(x, y, w, h, face, edge, title, body=None,
        title_size=10.2, body_size=8.8, lw=1.3, zorder=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.10",
        linewidth=lw, facecolor=face, edgecolor=edge, zorder=zorder,
    ))
    ax.text(x + w / 2, y + h - 0.20, title,
            ha="center", va="top", fontsize=title_size,
            fontweight="bold", color=edge, zorder=zorder + 1)
    if body:
        ax.text(x + w / 2, y + h - 0.55, body,
                ha="center", va="top", fontsize=body_size,
                color=DARK, linespacing=1.30, zorder=zorder + 1)


def arrow(x1, y1, x2, y2, color="#333", lw=1.6, dashed=False, scale=13):
    ls = (0, (4, 3)) if dashed else "-"
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=scale,
        linewidth=lw, color=color, linestyle=ls, zorder=3,
    ))


# ---------- banner ----------
ax.text(FIG_W / 2, FIG_H - 0.28,
        "Banking instantiation:  applying the framework to SASB FN-CB",
        ha="center", va="top", fontsize=13.4, fontweight="bold", color=DARK)
ax.text(FIG_W / 2, FIG_H - 0.55,
        "six commercial-banks topics  \u2192  20 sustainability reports  \u2192  per-report MMRI",
        ha="center", va="top", fontsize=10.0, color=MUTED, style="italic")

# ---------- band y-coords ----------
A_Y, A_H = 6.55, 1.40   # Layer A — benchmark + corpus
B_Y, B_H = 2.45, 3.95   # Layer B — pipeline + MMRI + validation
C_Y, C_H = 0.30, 1.95   # Layer C — outputs

band(A_Y, A_H, BAND_A, "Layer A   Regulatory benchmark  +  corpus", E_A)
band(B_Y, B_H, BAND_B, "Layer B   Computational assessment", E_B)
band(C_Y, C_H, BAND_C, "Layer C   Decision-oriented outputs", E_C)

# ============================================================
# Layer A  —  six SASB topics (left)  +  empirical corpus panel (right)
# ============================================================
topics = [
    ("Data Security",        "FN-CB-230a"),
    ("Financial Inclusion",  "FN-CB-240a"),
    ("ESG in Credit",        "FN-CB-410a"),
    ("Financed Emissions",   "FN-CB-410b"),
    ("Business Ethics",      "FN-CB-510a"),
    ("Systemic Risk",        "FN-CB-550a"),
]

# Two-line layout for Layer A:
#   row 1 (taller band): caption + corpus card
#   row 2: six topic cards, fully sized so titles never wrap
# Widen topic cards and push them down to leave the caption a clear line above.
tw, th, gap = 1.42, 0.62, 0.08
left_block_w = 6 * tw + 5 * gap
tx0 = 0.55
ty = A_Y + 0.10  # bottom of the band, leaving caption space above
for i, (t, c) in enumerate(topics):
    x = tx0 + i * (tw + gap)
    ax.add_patch(FancyBboxPatch(
        (x, ty), tw, th,
        boxstyle="round,pad=0.008,rounding_size=0.06",
        linewidth=1.1, facecolor=WHITE, edgecolor=E_A, zorder=2,
    ))
    ax.text(x + tw / 2, ty + th - 0.10, t,
            ha="center", va="top", fontsize=8.4,
            fontweight="bold", color=DARK)
    ax.text(x + tw / 2, ty + 0.07, c,
            ha="center", va="bottom", fontsize=7.2,
            color=MUTED, family="monospace")

# Caption sits in the strip between band header and the topic-card row
ax.text(tx0 + left_block_w / 2, ty + th + 0.16,
        "SASB Commercial Banks Standard (FN-CB)   \u2014   "
        r"$F=\{f_1,\ldots,f_6\}$",
        ha="center", va="bottom", fontsize=8.4, color=MUTED, style="italic")

# Empirical corpus card on the right of Layer A — same vertical extent as topic row
corp_x = tx0 + left_block_w + 0.35
corp_w = FIG_W - corp_x - 0.55
corp_y = ty
corp_h = th + 0.16  # slightly taller so it visually anchors the row
box(corp_x, corp_y, corp_w, corp_h, WHITE, E_A,
    "Corpus  (this study)",
    "Big Four AU banks: ANZ, CBA, NAB, Westpac\n"
    "2021 – 2025  \u2192  20 reports",
    title_size=9.4, body_size=8.2)

# ============================================================
# Layer B  —  three pipeline steps + MMRI + validation
# ============================================================
row_y, row_h = 4.75, 1.20

b1_x, b1_w = 0.55, 3.55
b2_x, b2_w = 4.40, 4.20
b3_x, b3_w = 8.90, 3.55

box(b1_x, row_y, b1_w, row_h, WHITE, E_B,
    "B1  Extract  &  retrieve",
    "PDF text extraction (pdfplumber)\n"
    r"$\rightarrow$ ~150-word passages"
    "\n"
    r"$\rightarrow$ top-$K$ passages per topic $f_i$",
    title_size=10.0, body_size=8.4)

box(b2_x, row_y, b2_w, row_h, WHITE, E_B,
    "B2  Score coverage   (LLM)",
    "Claude  |  Gemini   structured prompt\n"
    r"$C_{r,i}=\alpha\,\mathrm{Pres}+\beta\,\mathrm{Spec}+\gamma\,\mathrm{Quant}\;\in[0,1]$"
    "\n"
    r"$\alpha+\beta+\gamma=1$",
    title_size=10.0, body_size=8.4)

box(b3_x, row_y, b3_w, row_h, WHITE, E_B,
    "B3  Per-topic misalignment",
    r"$M_{r,i}=1-C_{r,i}\;\in[0,1]$"
    "\n"
    "0 = fully disclosed\n"
    "1 = silent on a required topic",
    title_size=10.0, body_size=8.4)

arrow(b1_x + b1_w, row_y + row_h / 2, b2_x, row_y + row_h / 2)
arrow(b2_x + b2_w, row_y + row_h / 2, b3_x, row_y + row_h / 2)

# MMRI block (centre-left) and Validation anchor (right)
mmri_y, mmri_h = 2.65, 1.85
mmri_x, mmri_w = 0.55, 8.85
val_x, val_w = 9.65, 2.80

box(mmri_x, mmri_y, mmri_w, mmri_h, C_MMRI_FILL, E_MMRI,
    "Materiality Misalignment Risk Index   (MMRI)",
    r"$\mathrm{MMRI}_r=\dfrac{\sum_i a_i\,w_i\,M_{r,i}}{\sum_i a_i\,w_i}\;\in[0,1]$"
    + "        "
    + r"$a_i\in\{0,1\}$  applicability,    $\sum_i w_i=1$"
    + "\n"
    + "this study:  "
    + r"$a_i=1\;\forall i$,    $w_i=1/6$  (equal-weight baseline)"
    + "\n"
    + r"reported as  $\bar{\mathrm{MMRI}}_r \pm$ 95% CI  over $k$ runs",
    title_size=11.0, body_size=9.1)

box(val_x, mmri_y, val_w, mmri_h, C_VAL_FILL, E_VAL,
    "Validation",
    "human-annotated\n"
    "reference KG\n\n"
    "ablation studies\n"
    r"+ repeated $k$ runs",
    title_size=10.0, body_size=8.6)

# Vertical drops B1/B2/B3 -> MMRI top edge
arrow(b1_x + b1_w / 2, row_y, b1_x + b1_w / 2, mmri_y + mmri_h)
arrow(b2_x + b2_w / 2, row_y, b2_x + b2_w / 2, mmri_y + mmri_h)
arrow(b3_x + b3_w / 2, row_y, b3_x + b3_w / 2, mmri_y + mmri_h)

# Validation feedback (dashed): one short arrow into each step
arrow(val_x, mmri_y + mmri_h * 0.72, b3_x + b3_w, row_y + 0.22,
      color=E_VAL, lw=1.0, dashed=True)
arrow(val_x, mmri_y + mmri_h * 0.50, b2_x + b2_w, row_y + 0.22,
      color=E_VAL, lw=1.0, dashed=True)
arrow(val_x, mmri_y + mmri_h * 0.28, b1_x + b1_w, row_y + 0.22,
      color=E_VAL, lw=1.0, dashed=True)

# Layer A -> B1: single clean entry from the corpus card down to B1 row
mid_top = (b1_x + b1_w / 2 + b2_x + b2_w / 2) / 2
arrow(mid_top, A_Y, mid_top, row_y + row_h, color=E_A, lw=1.6)
ax.text(mid_top + 0.15, A_Y - 0.15,
        "benchmark + reports",
        ha="left", va="top", fontsize=8.2, color=E_A, style="italic")

# ============================================================
# Layer C  —  three concrete outputs we produce
# ============================================================
out_y, out_h = 0.50, 1.55
out_titles = [
    "Per-report heatmap",
    "Topic-level bars",
    "MMRI trend",
]
out_bodies = [
    r"$M_{r,i}$ across all reports"
    + "\n"
    + "(bank \u00d7 year  \u00d7  topic)"
    + "\n"
    + "[fig 1]",
    "5-yr mean misalignment\n"
    "by bank \u00d7 topic\n"
    "[fig 2]",
    r"$\mathrm{MMRI}$ time-series"
    + "\n"
    + "per bank, 2021 – 2025\n"
    + "[fig 3]",
]
ow, ogap = 3.95, 0.30
total_o = 3 * ow + 2 * ogap
ox0 = (FIG_W - total_o) / 2
for i, (t, b) in enumerate(zip(out_titles, out_bodies)):
    x = ox0 + i * (ow + ogap)
    box(x, out_y, ow, out_h, WHITE, E_C, t, b,
        title_size=10.2, body_size=8.6)

# MMRI -> outputs row (single labelled arrow)
arrow(FIG_W / 2, mmri_y, FIG_W / 2, out_y + out_h - 0.05,
      color=E_MMRI, lw=2.0)
ax.text(FIG_W / 2 + 0.18, mmri_y - 0.18,
        "comparable risk signal  \u2192  decision-oriented outputs",
        ha="left", va="top", fontsize=8.4, color=E_MMRI, style="italic")

# Stakeholder ribbon under the outputs (one tight line, no boxes)
ax.text(FIG_W / 2, out_y - 0.10,
        "supports:  Investors  (disclosure-risk complement to ESG ratings)   \u00b7   "
        "Firms  (topic-level reporting gaps)   \u00b7   "
        "Regulators  (scalable alignment monitoring)",
        ha="center", va="top", fontsize=8.6, color=E_C, style="italic")

# ---------- footer legend ----------
ax.text(FIG_W / 2, 0.10,
        "solid arrows = data flow      dashed arrows = validation feedback",
        ha="center", va="center", fontsize=8.0, color=MUTED, style="italic")

plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
png = OUT_DIR / "framework_banking.png"
pdf = OUT_DIR / "framework_banking.pdf"
plt.savefig(png, dpi=240, bbox_inches="tight")
plt.savefig(pdf, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {png}")
print(f"Wrote {pdf}")
