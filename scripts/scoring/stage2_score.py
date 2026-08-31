"""
Stage 2 — auditable LLM scoring with full per-cell logs.

PURPOSE
  Wraps the LLM scoring step. There is ONE prompt template
  (../../prompts/scoring_prompt_v2.md) that gets rendered per cell
  in-memory at scoring time — no per-cell prompt files on disk.

ENTRY POINTS

  show <rid> <topic>
      Render and print one cell's prompt to stdout. The LLM (Claude in
      this conversation, or any other) reads it, then writes the
      matching .response.json into ./llm_scores_per_cell/.

  show_all
      Print every (rid, topic) prompt to stdout in sequence. Useful for
      piping to a script that calls the API.

  collect
      Read every .response.json in ./llm_scores_per_cell/, validate, join
      with the per-cell evidence file, and write:
        stage2_results_scores/stage2_llm_coverage_scores.json   (machine readable)
        stage2_results_scores/stage2_llm_coverage_scores.csv    (one row per cell)
        stage2_results_scores/stage2_audit_log.jsonl            (full audit, one cell per line)
        stage2_results_scores/stage2_audit_log.csv              (audit, CSV view)

PIPELINE POSITION
  Runs AFTER stage1_2_chunks_per_topic.py and feeds Stage 3 MMRI aggregation.

Run:  python3 pipeline/stage2_score.py show ANZ_2025_ESGReport data_security
      python3 pipeline/stage2_score.py collect
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

# Repository root, resolved relative to this file so the script runs from
# a clone at any location.
ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DIR = ROOT / "prompts"
EV_DIR = ROOT / "work" / "chunks_per_topic"
TOPICS_PATH = PIPELINE_DIR / "sasb_fncb_topics.json"
PROMPT_TEMPLATE_PATH = ROOT / "prompts" / "scoring_prompt_v2.md"

# Default results directory is Claude. Override with --results-dir when
# running for another model (e.g. GPT), and the script will read/write
# responses and scores inside <that dir>/{llm_scores_per_cell, stage2_results_scores}.
DEFAULT_RESULTS_DIR = ROOT / "results" / "claude"


def _init_paths(results_dir: Path) -> dict[str, Path]:
    responses_dir = results_dir / "llm_scores_per_cell"
    scores_dir = results_dir / "stage2_results_scores"
    responses_dir.mkdir(parents=True, exist_ok=True)
    scores_dir.mkdir(parents=True, exist_ok=True)
    return {
        "responses_dir": responses_dir,
        "scores_dir": scores_dir,
        "scores_json": scores_dir / "stage2_llm_coverage_scores.json",
        "scores_csv": scores_dir / "stage2_llm_coverage_scores.csv",
        "audit_jsonl": scores_dir / "stage2_audit_log.jsonl",
        "audit_csv": scores_dir / "stage2_audit_log.csv",
    }

ALLOWED = {0.0, 0.25, 0.5, 0.75, 1.0}


REPORT_LABELS = {
    "ANZ_2021_ESGSupplement": "ANZ 2021 ESG Supplement",
    "ANZ_2022_ESGSupplement": "ANZ 2022 ESG Supplement",
    "ANZ_2023_ESGSupplement": "ANZ 2023 ESG Supplement",
    "ANZ_2024_ESGSupplement": "ANZ 2024 ESG Supplement",
    "ANZ_2025_ESGReport": "ANZ 2025 ESG Report",
    "CBA_2021_AnnualReport_Sustainability": "CBA 2021 Annual Report (Sustainability section)",
    "CBA_2022_SustainabilityAppendix": "CBA 2022 Sustainability Appendix",
    "CBA_2023_SustainabilityReporting": "CBA 2023 Sustainability Reporting",
    "CBA_2024_SustainabilityReporting": "CBA 2024 Sustainability Reporting",
    "CBA_2025_SustainabilityAppendix": "CBA 2025 Sustainability Reporting Appendix",
    "NAB_2021_AnnualReview": "NAB 2021 Annual Review",
    "NAB_2022_ClimateReport": "NAB 2022 Climate Report (climate-only)",
    "NAB_2023_ClimateReport": "NAB 2023 Climate Report (climate-only)",
    "NAB_2024_ClimateReport": "NAB 2024 Climate Report (climate-only)",
    "NAB_2025_ClimateReport": "NAB 2025 Climate Report (climate-only)",
    "Westpac_2021_SustainabilitySupplement": "Westpac 2021 Sustainability Supplement",
    "Westpac_2022_SustainabilitySupplement": "Westpac 2022 Sustainability Supplement",
    "Westpac_2023_ClimateReport": "Westpac 2023 Climate Report (climate-only)",
    "Westpac_2024_ClimateReport": "Westpac 2024 Climate Report (climate-only)",
    "Westpac_2025_SustainabilityReport": "Westpac 2025 Sustainability Report",
}


def load_template_and_split() -> tuple[str, str]:
    """Return (system_prompt, user_template) parsed from the .md template."""
    md = PROMPT_TEMPLATE_PATH.read_text()
    sys_match = re.search(r"## SYSTEM PROMPT\s*\n+```(.*?)```", md, re.DOTALL)
    usr_match = re.search(r"## USER PROMPT.*?\n+```(.*?)```", md, re.DOTALL)
    if not sys_match or not usr_match:
        raise SystemExit("Could not parse SYSTEM/USER blocks from prompt template.")
    return sys_match.group(1).strip(), usr_match.group(1).strip()


def render_user_prompt(template: str, *, topic_def: dict,
                       report_id: str, evidence: dict) -> str:
    metrics_bul = "\n".join(
        f"  - {m['code']}  ({m['category']}): {m['description']}"
        for m in topic_def["metrics"]
    )
    evidence_bul = "\n".join(
        f"  - {e}" for e in topic_def["evidence_required_for_high_score"]
    )
    chunks_block = []
    for c in evidence["chunks"]:
        kinds = ",".join(c.get("kinds", []))
        force = "  [SASB-METRIC]" if c.get("force_included") else ""
        chunks_block.append(
            f"[{c['chunk_id']}  p.{c['page']}  {kinds}{force}]\n{c['text']}\n"
        )
    chunks_str = "\n".join(chunks_block) if chunks_block else "(no evidence retrieved)"

    rendered = template
    rendered = rendered.replace("{{topic_name}}", topic_def["name"])
    rendered = rendered.replace("{{topic_code_prefix}}", topic_def["code_prefix"])
    rendered = rendered.replace("{{topic_summary}}", topic_def["summary"])
    rendered = rendered.replace("{{topic_metrics_bulleted}}", metrics_bul)
    rendered = rendered.replace("{{topic_evidence_required_bulleted}}", evidence_bul)
    rendered = rendered.replace("{{report_id}}", report_id)
    rendered = rendered.replace("{{report_label}}",
                                REPORT_LABELS.get(report_id, report_id))
    rendered = rendered.replace("{{evidence_chunks_with_ids}}", chunks_str)
    return rendered


def assemble_full_prompt(rid: str, topic_key: str) -> str:
    schema = json.load(TOPICS_PATH.open())
    topics = schema["topics"]
    if topic_key not in topics:
        raise SystemExit(f"Unknown topic: {topic_key}")
    topic_def = topics[topic_key]
    ev_path = EV_DIR / f"{rid}__{topic_key}.json"
    if not ev_path.exists():
        raise SystemExit(f"No evidence file for {rid}__{topic_key}")
    evidence = json.load(ev_path.open())
    sys_prompt, usr_template = load_template_and_split()
    user_prompt = render_user_prompt(
        usr_template, topic_def=topic_def, report_id=rid, evidence=evidence
    )
    return ("=== SYSTEM PROMPT ===\n" + sys_prompt + "\n\n"
            "=== USER PROMPT ===\n" + user_prompt + "\n")


# ============================================================
# show — print one cell's prompt to stdout
# ============================================================
def cmd_show(rid: str, topic_key: str) -> None:
    print(assemble_full_prompt(rid, topic_key))


def cmd_show_all(paths: dict[str, Path]) -> None:
    responses_dir = paths["responses_dir"]
    for ef in sorted(p for p in EV_DIR.glob("*.json")
                     if not p.name.startswith("_")):
        rid, topic_key = ef.stem.split("__", 1)
        resp_path = responses_dir / f"{ef.stem}.response.json"
        if resp_path.exists():
            continue
        print(f"\n========== CELL: {rid} / {topic_key} ==========\n")
        print(assemble_full_prompt(rid, topic_key))


# ============================================================
# collect — validate responses, aggregate into scores file
# ============================================================
def parse_response(path: Path) -> dict:
    data = json.loads(path.read_text())
    for k in ("presence", "specificity", "quantification"):
        if k not in data:
            raise ValueError(f"{path.name}: missing key '{k}'")
        if float(data[k]) not in ALLOWED:
            raise ValueError(
                f"{path.name}: {k} = {data[k]} not in {sorted(ALLOWED)}"
            )
    if "citations" not in data or not isinstance(data["citations"], list):
        raise ValueError(f"{path.name}: missing or non-list 'citations'")
    return data


def cmd_collect(paths: dict[str, Path]) -> None:
    response_files = sorted(p for p in paths["responses_dir"].glob("*.response.json")
                            if not p.name.startswith("_"))
    print(f"Collecting {len(response_files)} responses...")

    scores: dict[str, dict] = {}
    audit_lines: list[str] = []
    for rf in response_files:
        stem = rf.stem.replace(".response", "")
        rid, topic_key = stem.split("__", 1)
        ev_path = EV_DIR / f"{stem}.json"
        if not ev_path.exists():
            print(f"  SKIP (no evidence file): {stem}")
            continue
        evidence = json.load(ev_path.open())
        try:
            resp = parse_response(rf)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  ERROR {stem}: {e}")
            continue

        scores.setdefault(rid, {})[topic_key] = {
            "presence": float(resp["presence"]),
            "specificity": float(resp["specificity"]),
            "quantification": float(resp["quantification"]),
            "a_i": evidence.get("a_i", 1),
            "n_evidence_chunks": evidence["n_returned"],
            "n_force_metric_chunks": evidence["n_force_included"],
            "n_table_chunks": evidence["n_table_chunks"],
            "n_ocr_chunks": evidence["n_ocr_chunks"],
        }
        audit_lines.append(json.dumps({
            "report_id": rid,
            "topic": topic_key,
            "presence": float(resp["presence"]),
            "specificity": float(resp["specificity"]),
            "quantification": float(resp["quantification"]),
            "presence_rationale": resp.get("presence_rationale", ""),
            "specificity_rationale": resp.get("specificity_rationale", ""),
            "quantification_rationale": resp.get("quantification_rationale", ""),
            "citations": resp["citations"],
            "evidence_chunk_ids": [c["chunk_id"] for c in evidence["chunks"]],
        }, ensure_ascii=False))

    scores_out = {
        "_file": "stage2_llm_coverage_scores.json",
        "_purpose": ("Per-cell LLM coverage scores (Stage 2). "
                     "P/S/Q in {0, 0.25, 0.5, 0.75, 1.0} per the canonical "
                     "scoring prompt v2."),
        "_writes": "feeds Stage 3 MMRI aggregation",
        "_n_reports_scored": len(scores),
        "_n_cells_scored": sum(len(v) for v in scores.values()),
        **scores,
    }
    paths["scores_json"].write_text(json.dumps(scores_out, indent=2))
    paths["audit_jsonl"].write_text("\n".join(audit_lines) + "\n")

    # CSV mirror of the scores (one row per cell, opens in Excel)
    with paths["scores_csv"].open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["report_id", "topic", "presence", "specificity",
                    "quantification", "coverage", "a_i",
                    "n_evidence_chunks", "n_force_metric_chunks",
                    "n_table_chunks", "n_ocr_chunks"])
        for rid, topics in scores.items():
            for topic_key, cell in topics.items():
                cov = (cell["presence"] + cell["specificity"]
                       + cell["quantification"]) / 3.0
                w.writerow([rid, topic_key,
                            cell["presence"], cell["specificity"],
                            cell["quantification"], f"{cov:.4f}",
                            cell["a_i"], cell["n_evidence_chunks"],
                            cell["n_force_metric_chunks"],
                            cell["n_table_chunks"], cell["n_ocr_chunks"]])

    # CSV mirror of the audit log (rationales + citations)
    with paths["audit_csv"].open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["report_id", "topic", "presence", "specificity",
                    "quantification", "presence_rationale",
                    "specificity_rationale", "quantification_rationale",
                    "citations", "evidence_chunk_ids"])
        for line in audit_lines:
            r = json.loads(line)
            w.writerow([r["report_id"], r["topic"],
                        r["presence"], r["specificity"], r["quantification"],
                        r["presence_rationale"], r["specificity_rationale"],
                        r["quantification_rationale"],
                        ";".join(r["citations"]),
                        ";".join(r["evidence_chunk_ids"])])

    print(f"\nWrote {paths['scores_json']}  ({len(scores)} reports, "
          f"{sum(len(v) for v in scores.values())} cells)")
    print(f"Wrote {paths['scores_csv'].name}  (CSV view of scores)")
    print(f"Wrote {paths['audit_jsonl'].name}  ({len(audit_lines)} audit lines)")
    print(f"Wrote {paths['audit_csv'].name}  (CSV view of audit log)")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["show", "show_all", "collect"])
    ap.add_argument("args", nargs="*",
                    help="for 'show': <report_id> <topic_key>")
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
                    help=("directory containing llm_scores_per_cell/ and "
                          "stage2_results_scores/ (default: Claude's)"))
    a = ap.parse_args()
    paths = _init_paths(a.results_dir)
    if a.cmd == "show":
        if len(a.args) < 2:
            ap.error("show requires <report_id> <topic_key>")
        cmd_show(a.args[0], a.args[1])
    elif a.cmd == "show_all":
        cmd_show_all(paths)
    elif a.cmd == "collect":
        cmd_collect(paths)


if __name__ == "__main__":
    main()
