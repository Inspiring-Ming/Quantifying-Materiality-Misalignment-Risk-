"""Build the anonymized package for double-anonymized peer review.

The working repository is not safe to deposit as-is: the README and the project
page carry the author's GitHub account name, and several documents reference the
repository URL. This script produces a clean copy with every identifying string
removed, then refuses to write the archive if any survive.

  python3 scripts/build_review_package.py

Output: review-package/  and  review-package.zip  (both git-ignored)

What is removed or rewritten:
  - the project-page and repository URLs (README, availability statement)
  - the GitHub account name anywhere it appears
  - docs/index.html, which is the personal project site
  - docs/ZENODO_DEPOSIT.md and docs/SUBMISSION_CHECKLIST.md, which are internal
    workflow notes naming the account
  - CITATION.cff author placeholders, set to Anonymous
  - git history (never copied — this builds from the working tree, not a clone)

What is kept, unchanged:
  - all data, results, prompts, figures and scripts
  - the data dictionary, corpus notes, environment notes and known issues
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "review-package"
ZIP_BASE = REPO / "review-package"

# Files that exist only to serve the identified project, or that describe the
# internal submission workflow. Not part of the research package.
EXCLUDE_FILES = {
    "docs/index.html",
    "docs/ZENODO_DEPOSIT.md",
    "docs/SUBMISSION_CHECKLIST.md",
    "docs/DATA_AVAILABILITY_STATEMENT.md",
    ".gitignore",
    # Internal tooling for preparing the submission, not part of the research
    # package. This file necessarily lists the identifying terms it screens for.
    "scripts/build_review_package.py",
    "scripts/build_url_sheet.py",
    # Scratch file used to collect the source URLs; its contents are already
    # merged into data/report_metadata.csv.
    "url_sheet.csv",
}
EXCLUDE_DIRS = {".git", "docs/img", "review-package", "__pycache__", ".venv"}

# Any of these appearing in the output is a hard failure.
FORBIDDEN = [
    "mingqin", "inspiring-ming", "mingchin", "t677215",
    "unsw", "cognitivo", "jasmin", "felix tan",
    "github.com", "github.io",
]

ANON_README_HEADER = """# Research data and reproducibility materials

Materials accompanying a manuscript currently under double-anonymized peer
review. Author, affiliation and venue details are withheld until publication.
"""


def copy_tree() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    for src in sorted(REPO.rglob("*")):
        rel = src.relative_to(REPO)
        parts = set(rel.parts)
        if parts & EXCLUDE_DIRS or any(str(rel).startswith(d) for d in EXCLUDE_DIRS):
            continue
        if str(rel) in EXCLUDE_FILES:
            continue
        if src.is_dir():
            continue
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def anonymize_readme() -> None:
    p = OUT / "README.md"
    t = p.read_text()

    # Replace the identified header block with the anonymous one.
    t = re.sub(r"\A# MMRI-ESG-Banking.*?(?=This repository contains)",
               ANON_README_HEADER + "\n", t, flags=re.S)
    t = t.replace("This repository contains", "This package contains")

    # Drop the project-page line and any repository references.
    t = "\n".join(l for l in t.splitlines()
                  if "github.io" not in l and "github.com" not in l)

    t = t.replace("MMRI-ESG-Banking/\n", "package/\n")
    t = t.replace("## Citation\n", "## Citation\n\nCitation details are withheld during anonymous review.\n")
    t = re.sub(r"> \[AUTHORS\][^\n]*\n", "", t)
    t = re.sub(r"Archived release of this repository: \*\*DOI \[ZENODO DOI\]\*\*\n", "", t)
    t = t.replace("Copyright (c) 2026 [AUTHORS]", "Copyright (c) 2026 (author withheld for review)")
    p.write_text(t)


def anonymize_misc() -> None:
    # CITATION.cff — creators become Anonymous.
    c = OUT / "CITATION.cff"
    if c.exists():
        t = c.read_text()
        t = re.sub(r'authors:\n(  - family-names: "\[FAMILY NAME\]"\n    given-names: "\[GIVEN NAME\]"\n)',
                   'authors:\n  - name: "Anonymous (author details withheld for peer review)"\n', t)
        t = re.sub(r'      - family-names: "\[FAMILY NAME\]"\n        given-names: "\[GIVEN NAME\]"\n',
                   '      - name: "Anonymous"\n', t)
        t = re.sub(r"^  # orcid:.*\n", "", t, flags=re.M)
        t = re.sub(r"^  # affiliation:.*\n", "", t, flags=re.M)
        c.write_text(t)

    # Licenses — strip the author placeholder.
    for name in ("LICENSE", "LICENSE-DATA"):
        p = OUT / name
        if p.exists():
            p.write_text(p.read_text().replace(
                "Copyright (c) 2026 [AUTHORS]",
                "Copyright (c) 2026 (author details withheld for peer review)"))

    # Any stray repository URL in the remaining docs.
    for p in OUT.rglob("*.md"):
        t = p.read_text()
        if "github" in t.lower():
            t = "\n".join(l for l in t.splitlines()
                          if "github.io" not in l and "github.com" not in l)
            p.write_text(t)


def scan() -> list[str]:
    hits = []
    for p in sorted(OUT.rglob("*")):
        if not p.is_file():
            continue
        try:
            t = p.read_text(errors="ignore").lower()
        except Exception:                                   # noqa: BLE001
            continue
        for term in FORBIDDEN:
            if term in t:
                hits.append(f"{p.relative_to(OUT)}: contains {term!r}")
    return hits


def main() -> int:
    print("Building anonymized review package ...")
    copy_tree()
    anonymize_readme()
    anonymize_misc()

    hits = scan()
    if hits:
        print("\nREFUSING to build the archive — identifying strings remain:\n")
        for h in hits:
            print(f"  {h}")
        print("\nFix the source or extend EXCLUDE_FILES, then re-run.")
        return 1

    shutil.make_archive(str(ZIP_BASE), "zip", root_dir=OUT.parent, base_dir=OUT.name)
    n = sum(1 for p in OUT.rglob("*") if p.is_file())
    size = ZIP_BASE.with_suffix(".zip").stat().st_size / 1e6

    print(f"\n  review-package/       {n} files, no identifying strings")
    print(f"  review-package.zip    {size:.1f} MB  <- upload this to Zenodo")
    print("\nVerify independently before depositing:")
    print("  grep -ri 'inspiring-ming\\|mingqin\\|github' review-package/ ; echo \"exit $?\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
