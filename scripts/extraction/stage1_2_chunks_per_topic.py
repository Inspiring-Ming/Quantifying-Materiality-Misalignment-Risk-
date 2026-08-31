"""
Stage 1.2 — split chunks into per-topic evidence (SASB-grounded retrieval).

PURPOSE
  For every (report, topic) pair, pick the small set of chunks from
  ../pipeline_stage1_outputs/chunks/<rid>.json that the LLM should actually
  read. Output one evidence file per cell. Retrieval is grounded in the
  SASB FN-CB topic schema (sasb_fncb_topics.json), not hand-typed
  keywords:

    1. Keyword-seed scoring         (from sasb_fncb_topics.json keyword_seeds)
    2. Verbatim SASB-metric phrases (force-include, e.g. "Scope 3", "G-SIB")
    3. Per-chunk word cap           (truncate any chunk > MAX_CHUNK_WORDS)
    4. Top-K selection              (final K chunks per cell)

PIPELINE POSITION
  Runs AFTER stage1_1_extract_chunks.py and BEFORE stage2_score.py.

INPUTS   ../pipeline_stage1_outputs/chunks/<rid>.json           (one per report)
         ./sasb_fncb_topics.json                        (topic schema)
OUTPUTS  ../pipeline_stage1_outputs/chunks_per_topic/<rid>__<topic>.json
                                                       (one per cell, 120 total)
         ../pipeline_stage1_outputs/chunks_per_topic/_manifest.json

Run:  python3 pipeline/stage1_2_chunks_per_topic.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Repository root, resolved relative to this file so the script runs from
# a clone at any location.
ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DIR = ROOT / "prompts"
CHUNKS_DIR = ROOT / "work" / "chunks"
TOPICS_PATH = PIPELINE_DIR / "sasb_fncb_topics.json"
OUT_EV_DIR = ROOT / "work" / "chunks_per_topic"
OUT_EV_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = OUT_EV_DIR / "_manifest.json"

# ------------ Tunables ------------
TOP_K = 5                 # final chunks per cell (compressed for in-conv scoring)
TABLE_BONUS = 2.0         # added to keyword score if chunk contains a table
OCR_BONUS = 0.5           # small boost for OCR-extracted text
MIN_KEYWORD_HITS = 1      # below this, chunk is dropped
MAX_CHUNK_WORDS = 350     # truncate any chunk longer than this when emitting
# Verbatim phrases that, if present, force-include the chunk.
# These come from the SASB metric descriptions.
FORCE_INCLUDE_PHRASES: dict[str, list[str]] = {
    "data_security": [
        "data breach", "personal data breach", "account holders affected",
        "notifiable data breach",
    ],
    "financial_inclusion": [
        "no-cost checking", "small business and community development",
        "financial literacy initiatives", "underbanked", "unbanked",
    ],
    "esg_credit_analysis": [
        "commercial and industrial credit exposure",
        "incorporation of ESG factors", "ESG factors in credit analysis",
        "Equator Principles", "ESRM",
    ],
    "financed_emissions": [
        "financed emissions", "scope 1", "scope 2", "scope 3",
        "PCAF", "gross exposure", "tCO2e",
    ],
    "business_ethics": [
        "monetary losses", "legal proceedings", "whistleblower",
        "anti-bribery", "anti-corruption",
    ],
    "systemic_risk": [
        "G-SIB", "D-SIB", "stress test", "CET1",
        "capital adequacy", "ICAAP",
    ],
}
# ---------------------------------


def load_topics() -> dict:
    with TOPICS_PATH.open() as f:
        return json.load(f)["topics"]


def applicability(report_id: str, topic_key: str, schema: dict) -> int:
    """Return a_i: 1 if the topic applies to this report type, else 0."""
    rules = schema.get("applicability_rules", {})
    if "Climate" in report_id and "ClimateReport" in report_id:
        clim = rules.get("climate_only_report", {})
        if topic_key in clim.get("does_not_apply", []):
            return 0
    return 1


def score_chunk(chunk: dict, kws: list[str],
                force_phrases: list[str]) -> tuple[float, int, bool]:
    """Return (score, n_kw_hits, has_force_phrase)."""
    txt_lower = chunk["text"].lower()
    n_hits = 0
    for kw in kws:
        n_hits += txt_lower.count(kw.lower())
    score = float(n_hits)

    if "table" in chunk.get("kinds", []):
        score += TABLE_BONUS
    if "ocr" in chunk.get("kinds", []):
        score += OCR_BONUS

    has_force = any(p.lower() in txt_lower for p in force_phrases)
    if has_force:
        # Force-include: massive boost so it always lands in top-K
        score += 100.0
    return score, n_hits, has_force


def retrieve(report_data: dict, topic_key: str, topic_def: dict) -> dict:
    kws = topic_def["keyword_seeds"]
    force_phrases = FORCE_INCLUDE_PHRASES.get(topic_key, [])

    scored = []
    for c in report_data["chunks"]:
        s, hits, force = score_chunk(c, kws, force_phrases)
        # A chunk is included ONLY if it has topic-keyword hits OR it
        # contains a SASB-mandated phrase. Tables alone are no longer
        # enough — that was pulling in unrelated quantitative tables
        # for climate-only reports on non-climate topics.
        if hits < MIN_KEYWORD_HITS and not force:
            continue
        scored.append({
            "chunk_id": c["chunk_id"],
            "page": c["page"],
            "kinds": c["kinds"],
            "n_words": c["n_words"],
            "kw_hits": hits,
            "score": round(s, 3),
            "force_included": force,
            "text": c["text"],
        })

    scored.sort(key=lambda x: (-x["score"], x["page"]))
    top = scored[:TOP_K]
    # Truncate any over-long kept chunk so prompts stay manageable.
    for r in top:
        words = r["text"].split()
        if len(words) > MAX_CHUNK_WORDS:
            r["text"] = " ".join(words[:MAX_CHUNK_WORDS]) + " [...truncated]"
            r["n_words_truncated"] = len(words) - MAX_CHUNK_WORDS
            r["n_words"] = MAX_CHUNK_WORDS
    return {
        "report_id": report_data["report_id"],
        "topic": topic_key,
        "n_candidates": len(scored),
        "n_returned": len(top),
        "n_force_included": sum(1 for r in top if r["force_included"]),
        "n_table_chunks": sum(1 for r in top if "table" in r.get("kinds", [])),
        "n_ocr_chunks": sum(1 for r in top if "ocr" in r.get("kinds", [])),
        "chunks": top,
    }


def main() -> None:
    schema = json.load(TOPICS_PATH.open())
    topics = schema["topics"]
    report_files = sorted(p for p in CHUNKS_DIR.glob("*.json")
                          if not p.name.startswith("_"))
    print(f"Stage 1.5: retrieving over {len(report_files)} reports "
          f"× {len(topics)} topics = {len(report_files) * len(topics)} cells\n")

    manifest_rows = []
    for rfile in report_files:
        rid = rfile.stem
        report_data = json.load(rfile.open())
        print(f"  {rid}")
        for tkey, tdef in topics.items():
            a_i = applicability(rid, tkey, schema)
            res = retrieve(report_data, tkey, tdef)
            res["a_i"] = a_i
            out_path = OUT_EV_DIR / f"{rid}__{tkey}.json"
            with out_path.open("w") as f:
                json.dump(res, f, indent=2, ensure_ascii=False)
            manifest_rows.append({
                "report_id": rid,
                "topic": tkey,
                "a_i": a_i,
                "n_candidates": res["n_candidates"],
                "n_returned": res["n_returned"],
                "n_force_included": res["n_force_included"],
                "n_table_chunks": res["n_table_chunks"],
                "n_ocr_chunks": res["n_ocr_chunks"],
            })

    manifest = {
        "_file": "_manifest.json",
        "_purpose": ("Audit log of SASB-grounded retrieval (Stage 1.5). "
                     "Per-cell counts of candidate chunks, returned chunks, "
                     "force-included SASB-metric chunks, structured tables, "
                     "and OCR-derived chunks."),
        "_writes": "chunks_per_topic/<report_id>__<topic>.json (one per cell)",
        "_used_by": "stage2_score.py",
        "_tunables": {
            "TOP_K": TOP_K,
            "TABLE_BONUS": TABLE_BONUS,
            "OCR_BONUS": OCR_BONUS,
            "MIN_KEYWORD_HITS": MIN_KEYWORD_HITS,
        },
        "cells": manifest_rows,
    }
    with MANIFEST_PATH.open("w") as f:
        json.dump(manifest, f, indent=2)

    n_cells = len(manifest_rows)
    n_table = sum(1 for r in manifest_rows if r["n_table_chunks"] > 0)
    n_force = sum(r["n_force_included"] for r in manifest_rows)
    print()
    print(f"Wrote {n_cells} per-cell evidence files to {OUT_EV_DIR}")
    print(f"  cells with at least one structured table: {n_table}/{n_cells}")
    print(f"  total force-included SASB-metric chunks:  {n_force}")
    print(f"Wrote manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
