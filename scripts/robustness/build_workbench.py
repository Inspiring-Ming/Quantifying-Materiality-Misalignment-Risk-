"""
Build annotation_workbench.html — single-file HTML annotation UI.

The workbench embeds all 30 cells (topic + retrieved evidence) into one
HTML page. The annotator opens the file in any browser, scrolls cell by
cell, picks P / S / Q from dropdowns and types optional notes, then clicks
"Download CSV" at the bottom. The downloaded file is saved manually as
annotations_filled.csv (overwrite the empty one), and the existing
compute_agreement.py reads it.

No server, no install — open the .html locally, save the .csv, run the
script. Browser autosaves form state to localStorage so closing/reopening
keeps your progress.

Run once:  python3 "Claude model experiment/ablation_and_variance/human_validation/build_workbench.py"
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

REF_DIR = Path(__file__).resolve().parent
ROOT = REF_DIR.parents[2]
TEXT_DIR = ROOT / "work"
SOURCE_CSV = REF_DIR / "annotations_filled.csv"
SASB_SCHEMA = ROOT / "prompts" / "sasb_fncb_topics.json"
OUT_HTML = REF_DIR / "annotation_workbench.html"


def load_cells() -> list[dict]:
    with SOURCE_CSV.open() as f:
        return list(csv.DictReader(f))


def load_sasb_schema() -> dict:
    """Load canonical SASB FN-CB topic schema used by the scoring pipeline."""
    return json.loads(SASB_SCHEMA.read_text())["topics"]


def read_evidence(path_rel: str) -> str:
    """Render v2 evidence (chunks_per_topic JSON) as plain text for the workbench."""
    p = ROOT / path_rel
    if not p.exists():
        return f"(evidence file not found: {path_rel})"
    data = json.loads(p.read_text())
    chunks = data.get("chunks", [])
    if not chunks:
        return "(no evidence retrieved for this cell)"
    blocks: list[str] = []
    for c in chunks:
        kinds = ",".join(c.get("kinds", []))
        force = "  [SASB-METRIC]" if c.get("force_included") else ""
        blocks.append(
            f"[{c['chunk_id']}  p.{c['page']}  {kinds}{force}]\n{c['text']}\n"
        )
    return "\n".join(blocks).strip()


CSS = """
:root {
  --bg: #fafaf7;
  --panel: #ffffff;
  --ink: #1f2328;
  --muted: #5b6370;
  --line: #d8d6cf;
  --accent: #2F5EA8;
  --accent-soft: #e9eef7;
  --warn: #9A4F00;
  --ok: #2E7D4F;
  --shadow: 0 1px 2px rgba(20,20,20,0.04);
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--ink);
  font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI",
        "Helvetica Neue", Arial, sans-serif;
}
header {
  position: sticky; top: 0; z-index: 50;
  background: #ffffffee; backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
  padding: 14px 24px;
  display: flex; align-items: center; gap: 16px;
}
header h1 {
  margin: 0; font-size: 16px; font-weight: 600;
}
header .progress {
  font-size: 13px; color: var(--muted);
}
header .actions { margin-left: auto; display: flex; gap: 8px; }
header button {
  font: inherit; cursor: pointer;
  background: var(--accent); color: white; border: 0;
  border-radius: 6px; padding: 8px 14px;
}
header button.ghost {
  background: transparent; color: var(--accent);
  border: 1px solid var(--accent);
}
header button:hover { filter: brightness(1.05); }

main { max-width: 1080px; margin: 24px auto 120px; padding: 0 20px; }

.guide {
  background: var(--accent-soft); border: 1px solid #c8d4ed;
  padding: 14px 18px; border-radius: 8px; margin-bottom: 24px;
  font-size: 13.5px;
}
.guide b { color: var(--accent); }
.guide ul { margin: 6px 0 0 18px; padding: 0; }
.guide li { margin: 2px 0; }

.cell {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  margin-bottom: 22px;
  box-shadow: var(--shadow);
}
.cell-head {
  display: flex; align-items: baseline; gap: 14px;
  padding: 14px 18px 10px; border-bottom: 1px solid #efece4;
  flex-wrap: wrap;
}
.cell-num {
  font-weight: 700; font-size: 15px; color: var(--accent);
  min-width: 56px;
}
.cell-report { font-weight: 600; font-size: 14.5px; }
.cell-topic {
  font-size: 13.5px; color: var(--muted);
}
.cell-topic .key {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px; color: #555;
}
.cell-desc { font-size: 13px; color: var(--muted); padding: 0 18px 8px; }

.context {
  margin: 0 18px 10px;
  border: 1px solid #c8d4ed;
  background: var(--accent-soft);
  border-radius: 8px;
}
.context > summary {
  cursor: pointer; padding: 9px 14px;
  font-size: 12.5px; font-weight: 600; color: var(--accent);
  list-style: none;
}
.context > summary::-webkit-details-marker { display: none; }
.context > summary::before {
  content: "\\25B8"; display: inline-block;
  margin-right: 8px; transition: transform 0.15s;
}
.context[open] > summary::before { transform: rotate(90deg); }
.context-body { padding: 4px 16px 14px; font-size: 12.8px; color: #2c3238; }
.context-body h4 {
  margin: 12px 0 4px; font-size: 12.5px; color: var(--accent);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.context-body p { margin: 4px 0; line-height: 1.55; }
.context-body ul { margin: 4px 0 0 18px; padding: 0; }
.context-body li { margin: 3px 0; line-height: 1.5; }
.context-body .metric-code {
  display: inline-block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11.4px; color: #fff; background: var(--accent);
  padding: 1px 6px; border-radius: 3px; margin-right: 6px;
}
.context-body .metric-cat {
  font-size: 11.2px; color: var(--muted); font-style: italic;
  margin-left: 4px;
}
.context-body .anchor-table {
  display: grid; grid-template-columns: 40px auto;
  row-gap: 2px; column-gap: 10px; margin-top: 4px;
}
.context-body .anchor-val {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 600; color: var(--accent);
}

.evidence {
  background: #f6f5ee;
  border-top: 1px solid #efece4;
  border-bottom: 1px solid #efece4;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12.5px; line-height: 1.55;
  white-space: pre-wrap; word-break: break-word;
  padding: 14px 18px;
  max-height: 360px; overflow-y: auto;
  color: #2c2c2c;
}
.evidence-toggle {
  display: inline-block; cursor: pointer; font-size: 12px;
  color: var(--accent); padding: 6px 18px; user-select: none;
}

.form {
  display: grid;
  grid-template-columns: repeat(3, 1fr) 2fr;
  gap: 12px; padding: 14px 18px;
}
.field label {
  display: block; font-size: 12px; color: var(--muted);
  margin-bottom: 4px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.field select, .field input[type=text] {
  width: 100%; font: inherit; padding: 8px 10px;
  border: 1px solid var(--line); border-radius: 6px;
  background: white;
}
.field select:invalid { color: #999; }
.cell.done { border-color: #b9d6c1; }
.cell.done .cell-num::after {
  content: " \\2713"; color: var(--ok);
}

footer {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: #ffffffee; backdrop-filter: blur(8px);
  border-top: 1px solid var(--line);
  padding: 12px 24px;
  display: flex; align-items: center; gap: 16px;
}
footer .status { font-size: 13px; color: var(--muted); }
footer .actions { margin-left: auto; display: flex; gap: 8px; }
footer button {
  font: inherit; cursor: pointer;
  background: var(--accent); color: white; border: 0;
  border-radius: 6px; padding: 9px 16px; font-weight: 600;
}
footer button.ghost {
  background: transparent; color: var(--warn);
  border: 1px solid var(--warn);
}
footer button:disabled { opacity: 0.5; cursor: not-allowed; }
"""


JS_TEMPLATE = """
const CELLS = __CELLS_JSON__;
const STORAGE_KEY = 'pwd_human_validation_v1';

function loadState() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
  catch (e) { return {}; }
}
function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function updateProgress() {
  const state = loadState();
  let done = 0;
  for (const c of CELLS) {
    const s = state[c.cell_idx] || {};
    if (s.P !== undefined && s.P !== '' &&
        s.S !== undefined && s.S !== '' &&
        s.Q !== undefined && s.Q !== '') {
      done++;
      document.getElementById('cell-' + c.cell_idx).classList.add('done');
    } else {
      document.getElementById('cell-' + c.cell_idx).classList.remove('done');
    }
  }
  document.getElementById('progress').textContent =
    done + ' / ' + CELLS.length + ' filled';
  document.getElementById('download-btn').disabled = (done === 0);
  return done;
}

function onChange(cellIdx, field, value) {
  const state = loadState();
  if (!state[cellIdx]) state[cellIdx] = {};
  state[cellIdx][field] = value;
  saveState(state);
  updateProgress();
}

function csvEscape(v) {
  const s = String(v ?? '');
  if (s.includes(',') || s.includes('"') || s.includes('\\n'))
    return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function downloadCSV() {
  const state = loadState();
  const headers = ['cell_idx','report_id','report_label','topic',
                   'topic_name','topic_description','evidence_file_path',
                   'P','S','Q','notes'];
  const lines = [headers.join(',')];
  for (const c of CELLS) {
    const s = state[c.cell_idx] || {};
    const row = [
      c.cell_idx, c.report_id, c.report_label, c.topic,
      c.topic_name, c.topic_description, c.evidence_file_path,
      s.P ?? '', s.S ?? '', s.Q ?? '', s.notes ?? ''
    ].map(csvEscape).join(',');
    lines.push(row);
  }
  const blob = new Blob([lines.join('\\n') + '\\n'],
                        {type: 'text/csv;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'annotations_filled.csv';
  document.body.appendChild(a); a.click();
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 0);
}

function clearAll() {
  if (!confirm('Clear all annotations? This cannot be undone.')) return;
  localStorage.removeItem(STORAGE_KEY);
  for (const c of CELLS) {
    document.getElementById('p-' + c.cell_idx).value = '';
    document.getElementById('s-' + c.cell_idx).value = '';
    document.getElementById('q-' + c.cell_idx).value = '';
    document.getElementById('n-' + c.cell_idx).value = '';
  }
  updateProgress();
}

function restoreFromState() {
  const state = loadState();
  for (const c of CELLS) {
    const s = state[c.cell_idx] || {};
    if (s.P !== undefined) document.getElementById('p-' + c.cell_idx).value = s.P;
    if (s.S !== undefined) document.getElementById('s-' + c.cell_idx).value = s.S;
    if (s.Q !== undefined) document.getElementById('q-' + c.cell_idx).value = s.Q;
    if (s.notes !== undefined) document.getElementById('n-' + c.cell_idx).value = s.notes;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  restoreFromState();
  updateProgress();
  document.getElementById('download-btn').addEventListener('click', downloadCSV);
  document.getElementById('download-btn-2').addEventListener('click', downloadCSV);
  document.getElementById('clear-btn').addEventListener('click', clearAll);
  document.querySelectorAll('.evidence-toggle').forEach(t => {
    t.addEventListener('click', () => {
      const ev = t.previousElementSibling;
      if (ev.style.maxHeight === 'none') {
        ev.style.maxHeight = '360px';
        t.textContent = 'Expand evidence \\u25BE';
      } else {
        ev.style.maxHeight = 'none';
        t.textContent = 'Collapse evidence \\u25B4';
      }
    });
  });
});
"""


SCORE_OPTIONS = [
    ("", "—"),
    ("0", "0.00  none"),
    ("0.25", "0.25  weak"),
    ("0.5", "0.50  moderate"),
    ("0.75", "0.75  strong"),
    ("1", "1.00  full"),
]


ANCHOR_GUIDANCE = {
    "P": [
        ("0.00", "topic not addressed at all"),
        ("0.25", "passing mention only"),
        ("0.50", "topic discussed but partial"),
        ("0.75", "topic substantively addressed"),
        ("1.00", "topic comprehensively addressed"),
    ],
    "S": [
        ("0.00", "no named policy, framework, or mechanism"),
        ("0.25", "generic statements, no named artefacts"),
        ("0.50", "some named policies/frameworks but limited detail"),
        ("0.75", "multiple named policies with meaningful detail"),
        ("1.00", "named policies + governance roles + process detail"),
    ],
    "Q": [
        ("0.00", "no numbers disclosed for this topic"),
        ("0.25", "one or two peripheral numbers"),
        ("0.50", "some key metrics disclosed but SASB metric missing"),
        ("0.75", "most SASB metrics present with units/context"),
        ("1.00", "all SASB metrics disclosed with methodology"),
    ],
}


def render_topic_context(topic_key: str, topic_info: dict) -> str:
    """Render the collapsible SASB context card inserted above the evidence."""
    if topic_info is None:
        return ""
    name = html.escape(topic_info.get("name", topic_key))
    code_prefix = html.escape(topic_info.get("code_prefix", ""))
    summary = html.escape(topic_info.get("summary", ""))

    metric_items = []
    for m in topic_info.get("metrics", []):
        metric_items.append(
            f'<li><span class="metric-code">{html.escape(m.get("code",""))}</span>'
            f'{html.escape(m.get("description",""))}'
            f'<span class="metric-cat"> ({html.escape(m.get("category",""))})</span>'
            f'</li>'
        )
    metrics_html = (
        "<ul>" + "".join(metric_items) + "</ul>"
        if metric_items else "<p><em>No metrics listed.</em></p>"
    )

    evidence_items = "".join(
        f"<li>{html.escape(item)}</li>"
        for item in topic_info.get("evidence_required_for_high_score", [])
    )
    evidence_html = (
        f"<ul>{evidence_items}</ul>" if evidence_items else ""
    )

    def _anchor_rows(key: str) -> str:
        rows = []
        for v, txt in ANCHOR_GUIDANCE[key]:
            rows.append(
                f'<div class="anchor-val">{v}</div>'
                f'<div>{html.escape(txt)}</div>'
            )
        return "".join(rows)

    anchors_html = (
        '<h4>P \u00b7 Presence</h4>'
        f'<div class="anchor-table">{_anchor_rows("P")}</div>'
        '<h4>S \u00b7 Specificity</h4>'
        f'<div class="anchor-table">{_anchor_rows("S")}</div>'
        '<h4>Q \u00b7 Quantification</h4>'
        f'<div class="anchor-table">{_anchor_rows("Q")}</div>'
    )

    return f"""
<details class="context">
  <summary>Topic context \u00b7 {name} ({code_prefix}) \u2014 click to expand</summary>
  <div class="context-body">
    <h4>SASB topic summary</h4>
    <p>{summary}</p>
    <h4>SASB metrics for this topic</h4>
    {metrics_html}
    <h4>Evidence required for a high score</h4>
    {evidence_html}
    <h4>P / S / Q anchor reminder</h4>
    {anchors_html}
  </div>
</details>
"""


def render_cell(c: dict, topic_info: dict) -> str:
    idx = c["cell_idx"]
    evidence = read_evidence(c["evidence_file_path"])
    rep_label = html.escape(c["report_label"])
    topic_name = html.escape(c["topic_name"])
    topic_key = html.escape(c["topic"])
    topic_desc = html.escape(c["topic_description"])
    ev_path = html.escape(c["evidence_file_path"])
    ev_html = html.escape(evidence)
    context_html = render_topic_context(c["topic"], topic_info)

    options = "".join(
        f'<option value="{html.escape(v)}">{html.escape(label)}</option>'
        for v, label in SCORE_OPTIONS
    )

    def select(field: str) -> str:
        return (
            f'<select id="{field}-{idx}" required '
            f'onchange="onChange({idx}, \'{field.upper()}\', this.value)">'
            f'{options}</select>'
        )

    return f"""
<section class="cell" id="cell-{idx}">
  <div class="cell-head">
    <div class="cell-num">#{idx}</div>
    <div class="cell-report">{rep_label}</div>
    <div class="cell-topic">{topic_name} &nbsp;<span class="key">{topic_key}</span></div>
  </div>
  <div class="cell-desc">{topic_desc} &nbsp; · &nbsp;
    <span style="color:#888">evidence: {ev_path}</span>
  </div>
  {context_html}
  <pre class="evidence">{ev_html}</pre>
  <div class="evidence-toggle">Expand evidence \u25BE</div>
  <div class="form">
    <div class="field"><label>P · Presence</label>{select('p')}</div>
    <div class="field"><label>S · Specificity</label>{select('s')}</div>
    <div class="field"><label>Q · Quantification</label>{select('q')}</div>
    <div class="field"><label>Notes (optional)</label>
      <input id="n-{idx}" type="text"
             placeholder="Optional. Start with UNCERTAIN if low confidence."
             oninput="onChange({idx}, 'notes', this.value)">
    </div>
  </div>
</section>
"""


def main() -> None:
    cells = load_cells()
    topics = load_sasb_schema()
    cells_for_js = [
        {
            "cell_idx": int(c["cell_idx"]),
            "report_id": c["report_id"],
            "report_label": c["report_label"],
            "topic": c["topic"],
            "topic_name": c["topic_name"],
            "topic_description": c["topic_description"],
            "evidence_file_path": c["evidence_file_path"],
        }
        for c in cells
    ]
    js = JS_TEMPLATE.replace(
        "__CELLS_JSON__",
        json.dumps(cells_for_js, ensure_ascii=False),
    )

    cells_html = "\n".join(render_cell(c, topics.get(c["topic"])) for c in cells)

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Human validation workbench — 30 cells</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Human validation — 30 cells</h1>
  <div class="progress" id="progress">0 / 30 filled</div>
  <div class="actions">
    <button class="ghost" id="clear-btn">Clear all</button>
    <button id="download-btn" disabled>Download CSV</button>
  </div>
</header>

<main>
  <div class="guide">
    <b>How to use:</b>
    <ul>
      <li>Read each cell's evidence panel. Click <i>Expand evidence</i> if a passage is cut off.</li>
      <li>Pick a value for <b>P</b>, <b>S</b>, <b>Q</b> from each dropdown
          (anchors: 0 / 0.25 / 0.50 / 0.75 / 1.00).</li>
      <li>Optional notes — start with <code>UNCERTAIN</code> if low confidence.</li>
      <li>Your work is saved automatically in this browser. You can close and re-open the page.</li>
      <li>When done, click <b>Download CSV</b>. Save it (overwrite) as
          <code>annotations_filled.csv</code> in this folder, then run
          <code>compute_agreement.py</code>.</li>
      <li><b>Blinding:</b> do not open
          <code>Claude model experiment/claude_results/stage2_results_scores/stage2_llm_coverage_scores.json</code>
          until after you finish all 30 cells.</li>
    </ul>
  </div>

  {cells_html}
</main>

<footer>
  <div class="status" id="footer-status">
    Tip: progress autosaves to this browser. To move work between machines, click Download CSV.
  </div>
  <div class="actions">
    <button id="download-btn-2">Download CSV</button>
  </div>
</footer>

<script>{js}</script>
</body>
</html>
"""

    OUT_HTML.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT_HTML}")
    print(f"  ({len(cells)} cells, {OUT_HTML.stat().st_size // 1024} KB)")
    print()
    print("Open this file in any browser:")
    print(f"  open '{OUT_HTML}'")


if __name__ == "__main__":
    main()
