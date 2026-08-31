"""Generate a minimal fill-in sheet for the 20 source URLs, and merge it back.

Filling source_url / access_date is the one step that cannot be derived from
files on disk. This script reduces it to editing two columns in one small CSV,
then writes the values back into data/report_metadata.csv without touching any
of the derived fields.

  python3 scripts/build_url_sheet.py            # create url_sheet.csv
  python3 scripts/build_url_sheet.py --merge    # merge it back, with checks

The sheet carries the publisher's own PDF title where one was embedded, which
is the most reliable way to confirm you have located the right document.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
META = REPO / "data" / "report_metadata.csv"
SHEET = REPO / "url_sheet.csv"

# Titles embedded in the source PDFs by the publishers themselves. Blank where
# the PDF carried no title. Used only as a locating aid in the sheet.
PDF_TITLES = {
    "ANZ_2021_ESGSupplement": "2021-esg-supplement",
    "ANZ_2022_ESGSupplement": "2022-anz-esg-supplement",
    "ANZ_2023_ESGSupplement": "ANZ 2023 ESG Supplement",
    "ANZ_2024_ESGSupplement": "ANZ 2024 ESG Supplement",
    "ANZ_2025_ESGReport": "ANZ 2025 ESG Report",
    "CBA_2021_AnnualReport_Sustainability": "",
    "CBA_2022_SustainabilityAppendix": "",
    "CBA_2023_SustainabilityReporting": "2023 Sustainability Reporting (pages 18-39 of Annual Report)",
    "CBA_2024_SustainabilityReporting": "CBA 2024 Sustainability Reporting (pages 20-47 of the Annual Report)",
    "CBA_2025_SustainabilityAppendix": "CBA 2025 Sustainability Reporting Appendix",
    "NAB_2021_AnnualReview": "2021 Annual Review",
    "NAB_2022_ClimateReport": "2022 Climate Report",
    "NAB_2023_ClimateReport": "2023 Climate Report",
    "NAB_2024_ClimateReport": "2024 Climate Report",
    "NAB_2025_ClimateReport": "2025-climate-report",
    "Westpac_2021_SustainabilitySupplement": "Sustainability Supplement 2021 - Westpac Banking Corporation",
    "Westpac_2022_SustainabilitySupplement": "Sustainability Supplement 2022 - Westpac Group",
    "Westpac_2023_ClimateReport": "",
    "Westpac_2024_ClimateReport": "2024 Climate Report",
    "Westpac_2025_SustainabilityReport": "2025 Sustainability Report",
}

LANDING = {
    "ANZ": "https://www.anz.com/about-us/esg/reporting/",
    "CBA": "https://www.commbank.com.au/about-us/investors/annual-reports.html",
    "NAB": "https://www.nab.com.au/about-us/investor-centre/financial-disclosures-and-reporting",
    "Westpac": "https://www.westpac.com.au/about-westpac/sustainability/performance-reports/",
}


def read_meta() -> tuple[list[str], list[str], list[dict]]:
    text = META.read_text().splitlines()
    comments = [l for l in text if l.startswith("#")]
    rows = list(csv.DictReader(l for l in text if not l.startswith("#")))
    return comments, list(rows[0].keys()), rows


def build() -> None:
    _, _, rows = read_meta()
    with SHEET.open("w", newline="") as fh:
        fh.write("# Fill in source_url and access_date, then run:\n")
        fh.write("#   python3 scripts/build_url_sheet.py --merge\n")
        fh.write("# access_date is ISO 8601 (e.g. 2026-08-31). Leave nothing blank.\n")
        fh.write("# pdf_title is the title embedded by the publisher - use it to confirm\n")
        fh.write("# you have found the right document. bank_landing_page is a starting point.\n")
        w = csv.DictWriter(fh, fieldnames=[
            "report_id", "report_title", "pdf_title", "bank_landing_page",
            "source_url", "access_date"])
        w.writeheader()
        for r in rows:
            w.writerow({
                "report_id": r["report_id"],
                "report_title": r["report_title"],
                "pdf_title": PDF_TITLES.get(r["report_id"], ""),
                "bank_landing_page": LANDING[r["bank"]],
                "source_url": r["source_url"],
                "access_date": r["access_date"],
            })
    print(f"Wrote {SHEET.relative_to(REPO)}")
    print("Fill the last two columns, then: python3 scripts/build_url_sheet.py --merge")


def merge() -> int:
    if not SHEET.exists():
        print(f"{SHEET.name} not found — run without --merge first.")
        return 1

    filled = {}
    with SHEET.open() as fh:
        for r in csv.DictReader(l for l in fh if not l.startswith("#")):
            filled[r["report_id"]] = (r["source_url"].strip(), r["access_date"].strip())

    comments, fields, rows = read_meta()

    problems, updated = [], 0
    for r in rows:
        url, acc = filled.get(r["report_id"], ("", ""))
        if not url:
            problems.append(f"{r['report_id']}: source_url is empty")
            continue
        if not re.match(r"^https://", url):
            problems.append(f"{r['report_id']}: source_url must start with https://")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", acc):
            problems.append(f"{r['report_id']}: access_date must be YYYY-MM-DD (got {acc!r})")
        else:
            try:
                d = date.fromisoformat(acc)
                if d > date.today():
                    problems.append(f"{r['report_id']}: access_date is in the future")
            except ValueError:
                problems.append(f"{r['report_id']}: access_date is not a real date")
        r["source_url"], r["access_date"] = url, acc
        updated += 1

    if problems:
        print("Not merged — fix these first:\n")
        for p in problems:
            print(f"  {p}")
        return 1

    with META.open("w", newline="") as fh:
        for c in comments:
            fh.write(c + "\n")
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Merged {updated} rows into {META.relative_to(REPO)}")
    print("\nNext:")
    print("  python3 scripts/fetch_reports.py --out /tmp/corpus_check   # confirm URLs serve the scored files")
    print("  python3 scripts/verify_repo.py                             # confirm the package still passes")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--merge", action="store_true",
                    help="merge the filled sheet back into report_metadata.csv")
    a = ap.parse_args()
    if a.merge:
        return merge()
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
