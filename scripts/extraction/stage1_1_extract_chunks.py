"""
Stage 1.1 — extract every chunk from each PDF (prose + tables + OCR + cleanup).

PURPOSE
  Extract every paragraph, structured table and (where needed) OCR block
  from the 20 source PDFs in ../reports/, save them as sentence-aware
  chunks (~250 words each, never mid-sentence, never mid-table), and
  optionally denoise (drop oversized "tables", number-free tables, and
  navigation-banner chunks).

PIPELINE POSITION
  PDF (../reports/)
    -> Stage 1.1 (this script): extract -> ../pipeline_stage1_outputs/chunks/<rid>.json
                                clean   -> denoises that same folder in place
  -> Stage 1.2 (stage1_2_chunks_per_topic.py): picks topic-relevant chunks
                                -> ../pipeline_stage1_outputs/chunks_per_topic/
  -> Stage 2 (stage2_score.py): renders prompts, LLM scores them
  -> Stage 3: aggregate to per-report MMRI

ENTRY POINTS

  extract     PDFs -> ../pipeline_stage1_outputs/chunks/<rid>.json + _manifest.json
  clean       Denoise ../pipeline_stage1_outputs/chunks/<rid>.json in place;
              backup to ../pipeline_stage1_outputs/chunks_raw_pre_clean/<rid>.json
  all         extract then clean (recommended)

Run:  python3 pipeline/stage1_1_extract_chunks.py extract
      python3 pipeline/stage1_1_extract_chunks.py clean
      python3 pipeline/stage1_1_extract_chunks.py all
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pdfplumber

# Repository root, resolved relative to this file so the script runs from
# a clone at any location.
ROOT = Path(__file__).resolve().parent.parent.parent
PDF_DIR = ROOT / "reports"
CHUNKS_DIR = ROOT / "work" / "chunks"
BACKUP_DIR = ROOT / "work" / "chunks_raw_pre_clean"
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = CHUNKS_DIR / "_manifest.json"

# ============================================================
# Tunables
# ============================================================
TARGET_WORDS = 250                  # chunk size target
MIN_WORDS = 80                      # below this we keep merging
MAX_WORDS = 380                     # above this we split mid-sentence reluctantly
OCR_TEXT_LEN_THRESHOLD = 200        # page <200 chars + has image => OCR
OCR_DPI = 200
OCR_LANG = "eng"

MAX_TABLE_WORDS = 600               # tables > this are page misfires
MIN_NUMERIC_CHARS_FOR_TABLE = 6     # tables need >=6 digit chars
NAV_NOISE_THRESHOLD = 0.40          # >40% nav-banner words => drop chunk
NAV_WORDS = {
    "overview", "contents", "introduction", "appendix",
    "financial", "wellbeing", "environmental", "sustainability",
    "housing", "fair", "responsible", "banking", "human", "rights",
    "employee", "inclusion", "additional", "information", "assurance",
    "opinion", "supplement", "report", "esg", "page", "section",
    "stakeholder", "engagement", "targets",
}


# ============================================================
# Extract — PDFs to chunks
# ============================================================
def normalise_whitespace(text: str) -> str:
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\(])")


def split_sentences(text: str) -> list[str]:
    if not text.strip():
        return []
    return [p.strip() for p in SENTENCE_END_RE.split(text) if p.strip()]


def table_to_markdown(table: list[list[str | None]], page_no: int,
                      tbl_idx: int) -> str:
    if not table:
        return ""
    cleaned = [[(c or "").strip().replace("\n", " ") for c in row]
               for row in table]
    n_cols = max(len(r) for r in cleaned)
    for r in cleaned:
        while len(r) < n_cols:
            r.append("")
    header = cleaned[0]
    body = cleaned[1:] if len(cleaned) > 1 else []
    if all(h == "" for h in header):
        header = [f"Col{i+1}" for i in range(n_cols)]
        body = cleaned
    lines = [f"\n[TABLE p.{page_no} #{tbl_idx}]"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    lines.append("[/TABLE]\n")
    return "\n".join(lines)


def maybe_ocr_page(pdf_path: Path, page_no: int, text_chars: int,
                   has_images: bool) -> str:
    if text_chars >= OCR_TEXT_LEN_THRESHOLD or not has_images:
        return ""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        sys.stderr.write(f"  OCR skipped (missing dep: {e})\n")
        return ""
    try:
        images = convert_from_path(
            str(pdf_path), dpi=OCR_DPI,
            first_page=page_no, last_page=page_no,
        )
        if not images:
            return ""
        ocr_text = pytesseract.image_to_string(images[0], lang=OCR_LANG)
        return f"\n[OCR p.{page_no}]\n{ocr_text.strip()}\n[/OCR]\n"
    except Exception as e:
        sys.stderr.write(f"  OCR failed on p.{page_no}: {e}\n")
        return ""


def chunk_page(page_text: str, page_no: int) -> list[dict]:
    chunks: list[dict] = []
    if not page_text.strip():
        return chunks

    blocks: list[tuple[str, str]] = []
    cursor = 0
    for m in re.finditer(
        r"\[TABLE p\.\d+ #\d+\].*?\[/TABLE\]|\[OCR p\.\d+\].*?\[/OCR\]",
        page_text, flags=re.DOTALL,
    ):
        if m.start() > cursor:
            blocks.append(("prose", page_text[cursor:m.start()]))
        kind = "table" if m.group(0).startswith("[TABLE") else "ocr"
        blocks.append((kind, m.group(0)))
        cursor = m.end()
    if cursor < len(page_text):
        blocks.append(("prose", page_text[cursor:]))

    buf_words: list[str] = []
    buf_kinds: set[str] = set()

    def flush() -> None:
        if not buf_words:
            return
        body = " ".join(buf_words).strip()
        if body:
            chunks.append({
                "page": page_no,
                "n_words": len(body.split()),
                "kinds": sorted(buf_kinds),
                "text": body,
            })
        buf_words.clear()
        buf_kinds.clear()

    for kind, blk in blocks:
        if kind in ("table", "ocr"):
            flush()
            chunks.append({
                "page": page_no,
                "n_words": len(blk.split()),
                "kinds": [kind],
                "text": blk.strip(),
            })
            continue

        for s in split_sentences(blk):
            sw = s.split()
            if len(buf_words) + len(sw) > TARGET_WORDS and len(buf_words) >= MIN_WORDS:
                flush()
            if len(sw) > MAX_WORDS:
                flush()
                chunks.append({
                    "page": page_no,
                    "n_words": len(sw),
                    "kinds": ["prose"],
                    "text": s,
                })
                continue
            buf_words.extend(sw)
            buf_kinds.add("prose")

    flush()
    return chunks


def extract_one_pdf(pdf_path: Path) -> dict:
    pdf_path = pdf_path.resolve()
    rid = pdf_path.stem
    chunks_all: list[dict] = []
    page_meta: list[dict] = []
    n_ocr_pages = 0
    n_tables = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            try:
                prose = page.extract_text() or ""
            except Exception:
                prose = ""
            prose = normalise_whitespace(prose)

            try:
                tables = page.find_tables() or []
            except Exception:
                tables = []
            table_md_blocks: list[str] = []
            for ti, t in enumerate(tables, start=1):
                try:
                    rows = t.extract()
                    if rows:
                        table_md_blocks.append(table_to_markdown(rows, page_no, ti))
                        n_tables += 1
                except Exception:
                    pass

            has_images = bool(page.images)
            ocr_block = maybe_ocr_page(pdf_path, page_no, len(prose), has_images)
            if ocr_block:
                n_ocr_pages += 1

            page_text = prose
            for tb in table_md_blocks:
                page_text += "\n" + tb
            if ocr_block:
                page_text += "\n" + ocr_block

            page_meta.append({
                "page": page_no,
                "n_chars_prose": len(prose),
                "n_tables": len(table_md_blocks),
                "ocr_used": bool(ocr_block),
                "n_images": len(page.images),
            })

            chunks_all.extend(chunk_page(page_text, page_no))

    for i, c in enumerate(chunks_all):
        c["chunk_id"] = f"{rid}#chunk_{i:04d}"

    try:
        rel = str(pdf_path.relative_to(ROOT))
    except ValueError:
        rel = str(pdf_path)
    return {
        "report_id": rid,
        "pdf_relpath": rel,
        "n_pages": len(page_meta),
        "n_chunks": len(chunks_all),
        "n_tables_extracted": n_tables,
        "n_ocr_pages": n_ocr_pages,
        "page_meta": page_meta,
        "chunks": chunks_all,
    }


def cmd_extract() -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    print(f"Stage 1 extract: {len(pdfs)} PDFs (prose + tables + targeted OCR)\n")

    manifest_rows = []
    for i, pdf in enumerate(pdfs, start=1):
        rid = pdf.stem
        print(f"[{i:>2}/{len(pdfs)}] {rid}")
        rec = extract_one_pdf(pdf)
        out_path = CHUNKS_DIR / f"{rid}.json"
        with out_path.open("w") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        manifest_rows.append({
            "report_id": rid,
            "pdf": rec["pdf_relpath"],
            "n_pages": rec["n_pages"],
            "n_chunks": rec["n_chunks"],
            "n_tables_extracted": rec["n_tables_extracted"],
            "n_ocr_pages": rec["n_ocr_pages"],
        })
        print(f"     pages={rec['n_pages']:>3}  chunks={rec['n_chunks']:>4}  "
              f"tables={rec['n_tables_extracted']:>3}  ocr_pages={rec['n_ocr_pages']}")

    manifest = {
        "_file": "_manifest.json",
        "_purpose": ("Audit of high-fidelity extraction (Stage 1). "
                     "Per-report counts of pages, chunks, tables and OCR pages."),
        "_writes": "chunks/<report_id>.json (one per report)",
        "_used_by": "stage1_2_chunks_per_topic.py and stage2_score.py",
        "_tunables": {
            "TARGET_WORDS": TARGET_WORDS, "MIN_WORDS": MIN_WORDS,
            "MAX_WORDS": MAX_WORDS,
            "OCR_TEXT_LEN_THRESHOLD": OCR_TEXT_LEN_THRESHOLD, "OCR_DPI": OCR_DPI,
        },
        "reports": manifest_rows,
    }
    with MANIFEST_PATH.open("w") as f:
        json.dump(manifest, f, indent=2)

    print("\nDone.")
    tot_pages = sum(r["n_pages"] for r in manifest_rows)
    tot_chunks = sum(r["n_chunks"] for r in manifest_rows)
    tot_tables = sum(r["n_tables_extracted"] for r in manifest_rows)
    tot_ocr = sum(r["n_ocr_pages"] for r in manifest_rows)
    print(f"  totals: {tot_pages} pages, {tot_chunks} chunks, "
          f"{tot_tables} tables, {tot_ocr} OCR'd pages")


# ============================================================
# Clean — denoise chunks in place
# ============================================================
def numeric_chars(s: str) -> int:
    return sum(1 for c in s if c.isdigit())


def nav_word_ratio(text: str) -> float:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return 0.0
    nav = sum(1 for w in words if w in NAV_WORDS)
    return nav / len(words)


def strip_empty_cells(text: str) -> str:
    text = re.sub(r"(\|\s*){4,}\|", "| | |", text)
    text = re.sub(r"^\s*\|\s*(\|\s*)*$\n?", "", text, flags=re.MULTILINE)
    return text


def keep_chunk(c: dict) -> tuple[bool, str]:
    n_words = c["n_words"]
    kinds = c.get("kinds", [])
    text = c["text"]
    if "table" in kinds and n_words > MAX_TABLE_WORDS:
        return False, f"table too big ({n_words} words > {MAX_TABLE_WORDS})"
    if "table" in kinds and numeric_chars(text) < MIN_NUMERIC_CHARS_FOR_TABLE:
        return False, "table has no numeric content"
    if nav_word_ratio(text) >= NAV_NOISE_THRESHOLD:
        return False, f"navigation noise ({nav_word_ratio(text):.0%})"
    return True, ""


def cmd_clean() -> None:
    if not CHUNKS_DIR.exists():
        raise SystemExit(f"chunks dir not found: {CHUNKS_DIR}")

    if BACKUP_DIR.exists():
        print(f"Backup already exists at {BACKUP_DIR}, leaving it.")
    else:
        shutil.copytree(CHUNKS_DIR, BACKUP_DIR)
        print(f"Backed up originals to {BACKUP_DIR}")

    files = sorted(p for p in BACKUP_DIR.glob("*.json")
                   if not p.name.startswith("_"))
    print(f"Cleaning {len(files)} report chunk files...\n")

    summary = []
    for f in files:
        rec = json.load(f.open())
        kept = []
        dropped = {"table_too_big": 0, "no_numbers": 0, "nav_noise": 0}
        for c in rec["chunks"]:
            keep, reason = keep_chunk(c)
            if not keep:
                if "too big" in reason:
                    dropped["table_too_big"] += 1
                elif "no numeric" in reason:
                    dropped["no_numbers"] += 1
                else:
                    dropped["nav_noise"] += 1
                continue
            c["text"] = strip_empty_cells(c["text"])
            c["n_words"] = len(c["text"].split())
            kept.append(c)

        n_before = len(rec["chunks"])
        rec["n_chunks"] = len(kept)
        rec["chunks"] = kept
        out_path = CHUNKS_DIR / f.name
        with out_path.open("w") as outf:
            json.dump(rec, outf, indent=2, ensure_ascii=False)

        summary.append({"report_id": rec["report_id"], "before": n_before,
                        "after": len(kept), "dropped": dict(dropped)})
        print(f"  {rec['report_id']:48s}  {n_before:>4} -> {len(kept):>4} chunks   "
              f"(dropped: table_too_big={dropped['table_too_big']}, "
              f"no_numbers={dropped['no_numbers']}, nav_noise={dropped['nav_noise']})")

    n_before = sum(s["before"] for s in summary)
    n_after = sum(s["after"] for s in summary)
    print(f"\nTotal chunks: {n_before} -> {n_after}  "
          f"({100*(n_before-n_after)/n_before:.1f}% dropped)")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("extract", "clean", "all"):
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd in ("extract", "all"):
        cmd_extract()
    if cmd in ("clean", "all"):
        cmd_clean()


if __name__ == "__main__":
    main()
