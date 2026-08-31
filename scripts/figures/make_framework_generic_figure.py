"""
Generic (industry-agnostic) framework — Figure 1 of the paper.

DESIGN PHILOSOPHY
-----------------
The figure communicates BOTH the framework's structural commitment and
its configurability:

  *fixed*         = the framework commits to this structure / formula
                    (solid white cell with brown border).
  *configurable*  = the user picks one of several options at this slot
                    (dashed cream cell with gear icon and named examples).
  *robustness*    = inline check-mark badge listing the evidence the
                    paper provides for the reliability of this step.

What is fixed in this version
-----------------------------
  - Coverage formula        C_{r,i} = alpha * Pres + beta * Spec + gamma * Quant
  - Misalignment formula    M_{r,i} = 1 - C_{r,i}
  - MMRI aggregation        MMRI_r = sum_i a_i w_i M_{r,i} / sum_i a_i w_i

What is configurable
--------------------
  Layer 1   corpus type, materiality benchmark
  Layer 2   PDF parser, passage splitter, topic retriever,
            language model, prompting approach,
            coverage weights alpha/beta/gamma,
            applicability a_i, MMRI topic weights w_i
  Validation    reference set, k repeated runs, ablations

Pair with: make_framework_banking_figure.py  (Figure 2, SASB FN-CB demo).

INPUTS   none (self-contained)
OUTPUTS  ./framework_generic.{png,pdf}   (Elsevier two-column-friendly)

Run:  python3 results/framework/make_framework_generic_figure.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# Repository root, resolved relative to this file.
ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIG_W, FIG_H = 14.4, 12.4
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")

# ---------- palette ----------
BAND_1 = "#EEF3FA"
BAND_2 = "#F7F2EA"
BAND_3 = "#EEF4EF"
E_INPUT = "#2F5EA8"
E_STEP = "#8A5A2B"
E_MMRI = "#6B2E8C"
E_OUT = "#2E7D4F"
E_VAL = "#9A7A0A"
WHITE = "#FFFFFF"
DARK = "#141414"
MUTED = "#606060"
PLUG_FILL = "#FBF8F3"
PLUG_EDGE = "#8A7A52"
C_MMRI_FILL = "#F6EDF8"
BADGE_FILL = "#FDF6DC"


# ---------- primitives ----------
def band(y, h, face, label, edge):
    ax.add_patch(Rectangle((0.20, y), FIG_W - 0.40, h,
                           facecolor=face, edgecolor="none", zorder=0))
    ax.text(0.38, y + h - 0.18, label,
            ha="left", va="top", fontsize=10.6, fontweight="bold",
            color=edge, style="italic")


def parent_card(x, y, w, h, edge, title, subtitle=None, face=WHITE,
                title_size=10.6, subtitle_size=8.4, lw=1.6, zorder=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.12",
        linewidth=lw, facecolor=face, edgecolor=edge, zorder=zorder,
    ))
    ax.text(x + 0.22, y + h - 0.18, title,
            ha="left", va="top", fontsize=title_size,
            fontweight="bold", color=edge, zorder=zorder + 1)
    if subtitle:
        ax.text(x + 0.22, y + h - 0.40, subtitle,
                ha="left", va="top", fontsize=subtitle_size,
                color=edge, style="italic", zorder=zorder + 1)


def fixed_cell(x, y, w, h, title, body=None, edge=E_STEP,
               title_size=8.8, body_size=8.0, zorder=4):
    """Solid white cell with thin border — the framework commits to this."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.008,rounding_size=0.07",
        linewidth=1.2, facecolor=WHITE, edgecolor=edge, zorder=zorder,
    ))
    ax.text(x + w / 2, y + h - 0.12, title,
            ha="center", va="top", fontsize=title_size,
            fontweight="bold", color=DARK, zorder=zorder + 1)
    if body:
        ax.text(x + w / 2, y + h - 0.36, body,
                ha="center", va="top", fontsize=body_size,
                color=DARK, linespacing=1.32, zorder=zorder + 1)


def plug_cell(x, y, w, h, title, options, edge=PLUG_EDGE,
              title_size=8.6, opt_size=7.6, zorder=4):
    """Dashed cream cell with gear icon — configurable slot with named examples."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.008,rounding_size=0.07",
        linewidth=1.1, facecolor=PLUG_FILL, edgecolor=edge, zorder=zorder,
        linestyle=(0, (4, 2.5)),
    ))
    ax.text(x + w / 2, y + h - 0.12, "\u2699  " + title,
            ha="center", va="top", fontsize=title_size,
            fontweight="bold", color=edge, zorder=zorder + 1)
    ax.text(x + w / 2, y + h - 0.36, options,
            ha="center", va="top", fontsize=opt_size,
            color=DARK, linespacing=1.32, zorder=zorder + 1)


def robustness_badge(x, y, w, text, height=0.42, fontsize=7.2, zorder=5):
    """Inline 'robustness checks' badge with check-mark."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, height,
        boxstyle="round,pad=0.004,rounding_size=0.04",
        linewidth=0.8, facecolor=BADGE_FILL, edgecolor=E_VAL,
        zorder=zorder,
    ))
    ax.text(x + w / 2, y + height / 2,
            "\u2713  robustness checks\n" + text,
            ha="center", va="center", fontsize=fontsize, color=E_VAL,
            fontweight="bold", linespacing=1.20, zorder=zorder + 1)


def arrow(x1, y1, x2, y2, color="#333", lw=1.5, scale=13, zorder=3):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=scale,
        linewidth=lw, color=color, zorder=zorder,
    ))


def curved_loop(x1, y1, x2, y2, color=E_STEP, lw=1.3, scale=12,
                rad=-0.50, zorder=3):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=scale,
        linewidth=lw, color=color, linestyle="-",
        connectionstyle=f"arc3,rad={rad}", zorder=zorder,
    ))


# ---------- banner ----------
ax.text(FIG_W / 2, FIG_H - 0.30,
        "A three-layer framework for assessing disclosure-materiality misalignment",
        ha="center", va="top", fontsize=14.0, fontweight="bold", color=DARK)
ax.text(FIG_W / 2, FIG_H - 0.62,
        "fixed structure  +  configurable components   "
        "\u2192   reusable across industries, corpora, and language models",
        ha="center", va="top", fontsize=10.2, color=MUTED, style="italic")

# ---------- legend ----------
leg_y = FIG_H - 1.00
leg_h = 0.32
legend_w = 8.40
leg_x = (FIG_W - legend_w) / 2
ax.add_patch(FancyBboxPatch((leg_x, leg_y - leg_h / 2),
                            legend_w, leg_h,
                            boxstyle="round,pad=0.01,rounding_size=0.05",
                            linewidth=0.7, facecolor="#FAFAFA",
                            edgecolor="#D0D0D0", zorder=1))


def _legend_item(x_start, swatch_face, swatch_edge, label, label_color,
                 swatch_linestyle="solid"):
    sw, sh = 0.26, 0.20
    ax.add_patch(FancyBboxPatch((x_start, leg_y - sh / 2), sw, sh,
                                boxstyle="round,pad=0.002,rounding_size=0.04",
                                linewidth=1.0, facecolor=swatch_face,
                                edgecolor=swatch_edge, zorder=2,
                                linestyle=swatch_linestyle))
    ax.text(x_start + sw + 0.10, leg_y, label,
            ha="left", va="center", fontsize=8.2, color=label_color)


_legend_item(leg_x + 0.30, WHITE, DARK,
             "fixed (framework structure)", DARK)
_legend_item(leg_x + 3.20, PLUG_FILL, PLUG_EDGE,
             "\u2699 configurable component", PLUG_EDGE,
             swatch_linestyle=(0, (4, 2.5)))
_legend_item(leg_x + 5.95, BADGE_FILL, E_VAL,
             "\u2713 robustness-checked component", E_VAL)

# ---------- band y-coordinates (bottom up) ----------
L3_Y, L3_H = 0.45, 1.70
L2_Y, L2_H = 2.30, 7.20
L1_Y, L1_H = 9.65, 1.40

band(L1_Y, L1_H, BAND_1,
     "Layer 1   Corpus and benchmark definition", E_INPUT)
band(L2_Y, L2_H, BAND_2,
     "Layer 2   Evidence retrieval, disclosure scoring, and MMRI aggregation",
     E_STEP)
band(L3_Y, L3_H, BAND_3,
     "Layer 3   Decision-relevant outputs", E_OUT)

# ============================================================
# Layer 1 — two input cards
# ============================================================
margin = 0.55
input_gap = 0.30
L1_CARD_Y = L1_Y + 0.14
L1_CARD_H = L1_H - 0.50
input_total_w = FIG_W - 2 * margin - input_gap
input_w = input_total_w / 2
docs_x = margin
bench_x = docs_x + input_w + input_gap

parent_card(docs_x, L1_CARD_Y, input_w, L1_CARD_H, E_INPUT,
            "Select firm reports & reporting years",
            subtitle=r"firms $\times$ years   \u2192   "
                     + r"documents $\{r_1,\ldots,r_m\}$",
            title_size=10.4, subtitle_size=8.4, lw=1.4)
ax.text(docs_x + 0.22, L1_CARD_Y + 0.14,
        "e.g. annual sustainability reports  \u00b7  integrated reports  "
        "\u00b7  10-K / annual reports  \u00b7  CDP / TCFD filings",
        ha="left", va="bottom", fontsize=7.8, color=DARK)

parent_card(bench_x, L1_CARD_Y, input_w, L1_CARD_H, E_INPUT,
            "Select industry materiality framework",
            subtitle=r"benchmark topics  $F = \{f_1, f_2, \ldots, f_n\}$",
            title_size=10.4, subtitle_size=8.4, lw=1.4)
# topic chips
topics = [r"$f_1$", r"$f_2$", r"$f_3$", r"$f_4$", r"$\ldots$", r"$f_n$"]
chip_h = 0.30
chip_y = L1_CARD_Y + 0.10
chip_pad = 0.22
chip_gap = 0.08
n_chip = len(topics)
chip_total_w = input_w - 2 * chip_pad
chip_w = (chip_total_w - (n_chip - 1) * chip_gap) / n_chip
for i, t in enumerate(topics):
    cx = bench_x + chip_pad + i * (chip_w + chip_gap)
    ax.add_patch(FancyBboxPatch(
        (cx, chip_y), chip_w, chip_h,
        boxstyle="round,pad=0.006,rounding_size=0.05",
        linewidth=0.9, facecolor=WHITE, edgecolor=E_INPUT, zorder=3,
    ))
    ax.text(cx + chip_w / 2, chip_y + chip_h / 2, t,
            ha="center", va="center", fontsize=8.6, fontweight="bold",
            color=DARK)
ax.text(bench_x + input_w / 2, chip_y + chip_h + 0.06,
        "e.g. SASB  \u00b7  GRI  \u00b7  ESRS  \u00b7  TCFD  "
        "\u00b7  TNFD  \u00b7  CSRD",
        ha="center", va="bottom", fontsize=7.8, color=MUTED, style="italic")

# ============================================================
# Layer 2 — Extract row at top, then 3-step row beneath, MMRI rightmost
# ============================================================
extract_top = L2_Y + L2_H - 0.55
extract_h = 1.35
extract_x = margin + 1.30
extract_w = FIG_W - 2 * margin - 2.60
extract_y = extract_top - extract_h

row_gap_vertical = 0.65
l2_row_bot = L2_Y + 0.85
l2_row_top = extract_y - row_gap_vertical
l2_box_h = l2_row_top - l2_row_bot
l2_row_w = FIG_W - 2 * margin
l2_gap = 0.28
w_b2 = l2_row_w * 0.40
w_b3 = l2_row_w * 0.22
w_mmri = l2_row_w * 0.34
total_w = w_b2 + w_b3 + w_mmri + 2 * l2_gap
delta = (l2_row_w - total_w) / 3
w_b2 += delta
w_b3 += delta
w_mmri += delta

b2_x = margin
b3_x = b2_x + w_b2 + l2_gap
mmri_x = b3_x + w_b3 + l2_gap
l2_box_y = l2_row_top - l2_box_h

# ---- Extract macro (per document) ----
parent_card(extract_x, extract_y, extract_w, extract_h, E_STEP,
            "Extract topic-relevant evidence",
            subtitle="per document   \u2014   configurable: PDF text extractor"
                     "  \u00b7  passage splitter  \u00b7  topic retriever",
            title_size=11.0, subtitle_size=8.4)
ext_inner_y = extract_y + 0.18
ext_inner_h = extract_h - 0.68
plug_cell(extract_x + 0.24, ext_inner_y, extract_w - 0.48, ext_inner_h,
          "tool examples",
          "pdfplumber  \u00b7  PyMuPDF  \u00b7  OCR         "
          "\u00b7         keyword  \u00b7  BM25  \u00b7  embedding-based  "
          "\u00b7  hybrid retrieval",
          edge=PLUG_EDGE, title_size=8.6, opt_size=7.8)

# Arrows from Layer 1 inputs into Extract
arrow(docs_x + input_w * 0.55, L1_Y + 0.08,
      extract_x + extract_w * 0.30, extract_y + extract_h,
      color=E_INPUT, lw=1.3, scale=12)
arrow(bench_x + input_w * 0.45, L1_Y + 0.08,
      extract_x + extract_w * 0.70, extract_y + extract_h,
      color=E_INPUT, lw=1.3, scale=12)

# Extract -> Score arrow (clean two-segment)
extract_out_x = extract_x + extract_w * 0.18
b2_entry_x = b2_x + w_b2 * 0.18
b2_top_y = l2_row_top
mid_y = (extract_y + b2_top_y) / 2
ax.plot([extract_out_x, extract_out_x], [extract_y, mid_y],
        color=E_STEP, lw=1.5, zorder=3)
ax.plot([extract_out_x, b2_entry_x], [mid_y, mid_y],
        color=E_STEP, lw=1.5, zorder=3)
arrow(b2_entry_x, mid_y, b2_entry_x, b2_top_y + 0.02,
      color=E_STEP, lw=1.5, scale=12)
ax.text((extract_out_x + b2_entry_x) / 2, mid_y + 0.04,
        r"top-$K$ passages per topic",
        ha="center", va="bottom", fontsize=8.0, color=E_STEP, style="italic")

# ---- Score (B2), Misalignment (B3), MMRI macros ----
parent_card(b2_x, l2_box_y, w_b2, l2_box_h, E_STEP,
            "Score topic-level disclosure coverage",
            subtitle="per topic   \u2014   configurable: language model, prompting "
                     r"approach, weights $\alpha,\beta,\gamma$",
            title_size=11.0, subtitle_size=8.4)
parent_card(b3_x, l2_box_y, w_b3, l2_box_h, E_STEP,
            "Convert to misalignment",
            subtitle="per topic",
            title_size=11.0, subtitle_size=8.4)
parent_card(mmri_x, l2_box_y, w_mmri, l2_box_h, E_MMRI,
            "Aggregate to MMRI",
            subtitle=r"across topics   \u2014   configurable: applicability $a_i$,"
                     r" topic weights $w_i$",
            title_size=11.0, subtitle_size=8.4, face=C_MMRI_FILL)

ay_row = l2_box_y + l2_box_h * 0.50
arrow(b2_x + w_b2, ay_row, b3_x, ay_row, color=E_STEP, lw=1.6, scale=14)
arrow(b3_x + w_b3, ay_row, mmri_x, ay_row, color=E_MMRI, lw=1.8, scale=14)

ax.text((b2_x + w_b2 + b3_x) / 2, ay_row + 0.14,
        r"$C_{r,i}$", ha="center", va="bottom",
        fontsize=9.6, fontweight="bold", color=E_STEP)
ax.text((b3_x + w_b3 + mmri_x) / 2, ay_row + 0.14,
        r"$M_{r,i}$", ha="center", va="bottom",
        fontsize=9.6, fontweight="bold", color=E_MMRI)

# Topic loop arrow under B2..B3
loop_start_x = b3_x + w_b3 * 0.35
loop_end_x = b2_x + w_b2 * 0.75
loop_caption_y = l2_box_y - 0.45
curved_loop(loop_start_x, l2_box_y, loop_end_x, l2_box_y,
            color=E_STEP, lw=1.3, scale=12, rad=-0.55)
ax.text((loop_start_x + loop_end_x) / 2, loop_caption_y,
        "repeated for each materiality topic",
        ha="center", va="center", fontsize=8.6, color=E_STEP,
        fontweight="bold", style="italic")

# ---- B2 interior: language model + prompt + weights + coverage formula + badge ----
ci_pad = 0.22
cell_gap = 0.14
inner_top_b2 = l2_box_y + l2_box_h - 0.60
inner_bot_b2 = l2_box_y + 0.22
inner_h_b2 = inner_top_b2 - inner_bot_b2

row_gap = 0.10
badge_h = 0.46
row_a_h = inner_h_b2 * 0.24
row_b_h = inner_h_b2 * 0.18
row_c_h = inner_h_b2 - row_a_h - row_b_h - badge_h - 3 * row_gap

row_a_y = inner_top_b2 - row_a_h
row_b_y = row_a_y - row_b_h - row_gap
row_c_y = row_b_y - row_c_h - row_gap
row_d_y = row_c_y - badge_h - row_gap

sub_w_b2 = (w_b2 - 2 * ci_pad - cell_gap) / 2
plug_cell(b2_x + ci_pad, row_a_y, sub_w_b2, row_a_h,
          "language model",
          "Claude  \u00b7  Gemini  \u00b7  OpenAI GPT  \u00b7  Llama",
          title_size=8.8, opt_size=7.6)
plug_cell(b2_x + ci_pad + sub_w_b2 + cell_gap, row_a_y,
          sub_w_b2, row_a_h,
          "prompting approach",
          "zero-shot  \u00b7  few-shot  \u00b7  chain-of-thought  "
          "\u00b7  structured JSON",
          title_size=8.8, opt_size=7.6)

plug_cell(b2_x + ci_pad, row_b_y, w_b2 - 2 * ci_pad, row_b_h,
          r"coverage weights  $\alpha,\beta,\gamma$   (within a topic)",
          r"equal $\alpha=\beta=\gamma=1/3$"
          + "   \u00b7   domain-tuned   \u00b7   stakeholder-elicited",
          title_size=8.6, opt_size=7.4)

fixed_cell(b2_x + ci_pad, row_c_y, w_b2 - 2 * ci_pad, row_c_h,
           "coverage score  (fixed)",
           r"$C_{r,i} = \alpha\,\mathrm{Pres} + \beta\,\mathrm{Spec} "
           r"+ \gamma\,\mathrm{Quant}$"
           + "\n"
           + r"$\alpha + \beta + \gamma = 1,\ \ C_{r,i} \in [0,1]$",
           edge=E_STEP, title_size=9.0, body_size=8.2)

robustness_badge(b2_x + ci_pad, row_d_y, w_b2 - 2 * ci_pad,
                 "reference set  \u00b7  "
                 + r"repeated $k$ runs"
                 + "  \u00b7  "
                 + r"ablation over $\alpha,\beta,\gamma$ / prompt / model",
                 height=badge_h, fontsize=7.0)

# ---- B3 interior: misalignment formula + applicability ----
b3_ipad = 0.18
b3_inner_top = l2_box_y + l2_box_h - 0.60
b3_inner_bot = l2_box_y + 0.22
b3_inner_h = b3_inner_top - b3_inner_bot
b3_cell_h = (b3_inner_h - 0.18) / 2

fixed_cell(b3_x + b3_ipad, b3_inner_top - b3_cell_h,
           w_b3 - 2 * b3_ipad, b3_cell_h,
           "misalignment  (fixed)",
           r"$M_{r,i} = 1 - C_{r,i} \in [0,1]$" + "\n"
           "0 = fully disclosed\n1 = silent on required topic",
           edge=E_STEP, title_size=9.0, body_size=8.0)
plug_cell(b3_x + b3_ipad, b3_inner_bot,
          w_b3 - 2 * b3_ipad, b3_cell_h,
          r"applicability  $a_i \in \{0,1\}$",
          "marks topics that do not apply\nto every firm",
          title_size=9.0, opt_size=7.6)

# ---- MMRI interior: aggregation formula + topic weights + badge ----
mm_pad = 0.22
mm_top = l2_box_y + l2_box_h - 0.60
mm_bot = l2_box_y + 0.22
mm_h = mm_top - mm_bot

mm_row_gap = 0.10
mm_badge_h = 0.46
mm_weights_h = mm_h * 0.22
mm_formula_h = mm_h - mm_weights_h - mm_badge_h - 2 * mm_row_gap

mm_formula_y = mm_top - mm_formula_h
mm_w_y = mm_formula_y - mm_weights_h - mm_row_gap
mm_bad_y = mm_w_y - mm_badge_h - mm_row_gap

mm_ww = w_mmri - 2 * mm_pad
fixed_cell(mmri_x + mm_pad, mm_formula_y, mm_ww, mm_formula_h,
           "aggregation formula  (fixed)",
           r"$\mathrm{MMRI}_r = \dfrac{\sum_i a_i\,w_i\,M_{r,i}}"
           r"{\sum_i a_i\,w_i} \in [0,1]$"
           + "\n"
           + r"$a_i \in \{0,1\},\ \ \sum_i w_i = 1$"
           + "\n"
           + r"report mean $\bar{\mathrm{MMRI}}_r$  with  95% CI over $k$ runs",
           edge=E_MMRI, title_size=9.4, body_size=8.4)

plug_cell(mmri_x + mm_pad, mm_w_y, mm_ww, mm_weights_h,
          r"topic weights  $w_i$   (across topics)",
          r"equal $w_i = 1/n$"
          + "   \u00b7   investor-survey   \u00b7   severity-adjusted",
          title_size=8.8, opt_size=7.4)

robustness_badge(mmri_x + mm_pad, mm_bad_y, mm_ww,
                 r"repeated $k$ runs"
                 + "  \u00b7  "
                 + r"ablation over $w_i$"
                 + "  \u00b7  ensemble across language models",
                 height=mm_badge_h, fontsize=7.0)

# ============================================================
# Layer 3 — three output cards
# ============================================================
LC_HEADER = 0.40
l3_out_y = L3_Y + 0.20
l3_out_h = L3_H - LC_HEADER - 0.30
out_titles = ["Per-document heatmap", "Topic-level profile", "MMRI trend"]
out_bodies = [
    r"$M_{r,i}$ across all documents"
    + "\n" + r"(firm $\times$ period $\times$ topic)",
    "mean misalignment per firm\n"
    r"by topic  (cross-sectional)",
    r"$\mathrm{MMRI}_r$ time-series per firm"
    + "\n" + "across reporting periods",
]
ow, ogap = 4.30, 0.35
total_o = 3 * ow + 2 * ogap
ox0 = (FIG_W - total_o) / 2
for i, (t, b) in enumerate(zip(out_titles, out_bodies)):
    x = ox0 + i * (ow + ogap)
    fixed_cell(x, l3_out_y, ow, l3_out_h, t, b,
               edge=E_OUT, title_size=10.2, body_size=8.6)

# MMRI -> Layer 3 arrow with white background label
mmri_bottom_mid = mmri_x + w_mmri / 2
arrow(mmri_bottom_mid, L2_Y, mmri_bottom_mid, l3_out_y + l3_out_h + 0.02,
      color=E_MMRI, lw=2.0, scale=14)
label_y = (L2_Y + l3_out_y + l3_out_h) / 2
ax.add_patch(FancyBboxPatch((mmri_bottom_mid + 0.12, label_y - 0.13),
                            2.00, 0.26,
                            boxstyle="round,pad=0.004,rounding_size=0.04",
                            linewidth=0.0, facecolor=WHITE,
                            edgecolor="none", zorder=4))
ax.text(mmri_bottom_mid + 0.22, label_y,
        "comparable risk signal",
        ha="left", va="center", fontsize=8.4, color=E_MMRI,
        style="italic", zorder=5)

# Stakeholder ribbon
ax.text(FIG_W / 2, l3_out_y - 0.12,
        "supports:  Investors  (disclosure-risk complement to ESG ratings)   "
        "\u00b7   Firms  (topic-level reporting gaps)   "
        "\u00b7   Regulators  (scalable alignment monitoring)",
        ha="center", va="top", fontsize=8.4, color=E_OUT, style="italic")

# Bottom tagline (ported from GPT redesign — gives the figure a caption-style
# "so what" sentence)
ax.text(FIG_W / 2, 0.20,
        "The framework converts unstructured narrative ESG disclosures into a "
        "structured, comparable, and auditable materiality-misalignment signal.",
        ha="center", va="center", fontsize=9.4, color="#333", style="italic")

ax.text(FIG_W / 2, 0.04,
        "solid arrows = data flow      curved arrow = process repeated per topic      "
        "\u2713 robustness checks = inline evidence of reliability",
        ha="center", va="center", fontsize=7.6, color=MUTED, style="italic")

plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
png = OUT_DIR / "framework_generic.png"
pdf = OUT_DIR / "framework_generic.pdf"
plt.savefig(png, dpi=240, bbox_inches="tight")
plt.savefig(pdf, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {png}")
print(f"Wrote {pdf}")
