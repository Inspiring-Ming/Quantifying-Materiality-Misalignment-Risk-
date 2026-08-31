"""
Build annotations_template.csv for the human validation task (v2 evidence).

PURPOSE
  One-time builder for the empty CSV the annotator fills. Each row is one
  (report, topic) cell from the v2 pipeline (5 reports x 6 topics = 30 cells).

  The CSV's evidence_file_path column points to the per-cell evidence
  JSON in pipeline_stage1_outputs/chunks_per_topic/, which is the EXACT same evidence
  Claude scored. The HTML workbench (build_workbench.py) embeds those
  chunks visually for in-browser annotation; the CSV is the fallback for
  annotators who prefer Excel.

INPUTS   ../../../pipeline_stage1_outputs/chunks_per_topic/<rid>__<topic>.json
OUTPUT   ./annotations_template.csv

Run once:  python3 "Claude model experiment/ablation_and_variance/human_validation/build_csv_template.py"
"""

from __future__ import annotations

import csv
from pathlib import Path

REF_DIR = Path(__file__).resolve().parent
ROOT = REF_DIR.parents[2]
EV_DIR = ROOT / "work" / "chunks_per_topic"
OUT_CSV = REF_DIR / "annotations_template.csv"

REPORTS = [
    ("ANZ_2025_ESGReport", "ANZ 2025 ESG Report"),
    ("CBA_2025_SustainabilityAppendix", "CBA 2025 Sustainability Reporting Appendix"),
    ("Westpac_2021_SustainabilitySupplement", "Westpac 2021 Sustainability Supplement"),
    ("ANZ_2021_ESGSupplement", "ANZ 2021 ESG Supplement"),
    ("Westpac_2023_ClimateReport", "Westpac 2023 Climate Report (climate-only)"),
]

TOPICS = [
    ("data_security",
     "Data Security",
     "Customer data protection, breach risk, cyber controls. (SASB FN-CB-230a)"),
    ("financial_inclusion",
     "Financial Inclusion & Capacity Building",
     "Access for SMEs and underserved groups, financial literacy. (SASB FN-CB-240a)"),
    ("esg_credit_analysis",
     "ESG in Credit Analysis",
     "ESG factors in lending and credit risk decisions. (SASB FN-CB-410a)"),
    ("financed_emissions",
     "Financed Emissions",
     "Financed GHG emissions (Scope 1-3) and calculation methodology. (SASB FN-CB-410b)"),
    ("business_ethics",
     "Business Ethics",
     "Fraud, insider trading, whistleblower, governance. (SASB FN-CB-510a)"),
    ("systemic_risk",
     "Systemic Risk Management",
     "G-SIB score, stress testing, capital planning. (SASB FN-CB-550a)"),
]


def main() -> None:
    rows = []
    cell_idx = 0
    for rid, rlabel in REPORTS:
        for tkey, tname, tdesc in TOPICS:
            cell_idx += 1
            evidence_path = EV_DIR / f"{rid}__{tkey}.json"
            rel_path = evidence_path.relative_to(ROOT)
            rows.append({
                "cell_idx": cell_idx,
                "report_id": rid,
                "report_label": rlabel,
                "topic": tkey,
                "topic_name": tname,
                "topic_description": tdesc,
                "evidence_file_path": str(rel_path),
                "P": "",
                "S": "",
                "Q": "",
                "notes": "",
            })

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {OUT_CSV}  ({cell_idx} cells)")
    print()
    print("Recommended: open annotation_workbench.html in your browser")
    print("(it shows evidence inline). The CSV is the fallback entry point.")


if __name__ == "__main__":
    main()
