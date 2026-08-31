"""Re-download the 20-report corpus and verify it against the published checksums.

The source PDFs are copyright of the publishing banks and are therefore NOT
redistributed in this repository. This script rebuilds the corpus locally from
each bank's own website, then checks every file against the SHA-256 recorded in
data/report_metadata.csv — so you can confirm byte-for-byte that you hold the
same documents that produced the published scores.

Usage
  python3 scripts/fetch_reports.py                 # download into reports/
  python3 scripts/fetch_reports.py --verify-only   # just re-check what's there
  python3 scripts/fetch_reports.py --out DIR       # download somewhere else

Exit status is non-zero if any report is missing or fails its checksum.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
METADATA = REPO / "data" / "report_metadata.csv"
UA = "Mozilla/5.0 (compatible; MMRI-research-reproduction/1.0)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_rows() -> list[dict]:
    with METADATA.open() as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
        while chunk := resp.read(1 << 16):
            out.write(chunk)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=REPO / "reports",
                    help="directory to download into (default: reports/)")
    ap.add_argument("--verify-only", action="store_true",
                    help="do not download; only checksum what is already present")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    rows = load_rows()
    ok = missing = failed = 0

    for r in rows:
        name, want = r["pdf_filename"], r["sha256"]
        dest, url = args.out / name, r["source_url"].strip()

        if not dest.exists() and not args.verify_only:
            if not url:
                print(f"SKIP    {name}  (no source_url in report_metadata.csv)")
                missing += 1
                continue
            print(f"GET     {name}")
            try:
                fetch(url, dest)
            except Exception as exc:                     # noqa: BLE001
                print(f"ERROR   {name}: {exc}")
                dest.unlink(missing_ok=True)
                missing += 1
                continue

        if not dest.exists():
            print(f"MISSING {name}")
            missing += 1
        elif sha256(dest) == want:
            print(f"OK      {name}")
            ok += 1
        else:
            print(f"MISMATCH {name}\n"
                  f"         expected {want}\n"
                  f"         got      {sha256(dest)}")
            failed += 1

    print(f"\n{ok} verified, {failed} checksum mismatches, {missing} missing "
          f"(of {len(rows)} reports)")
    if failed:
        print("\nA mismatch usually means the bank has silently re-published the PDF at\n"
              "the same URL. The scores in this repository describe the version whose\n"
              "checksum is recorded in data/report_metadata.csv.")
    return 1 if (failed or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
