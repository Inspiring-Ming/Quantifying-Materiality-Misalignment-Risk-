# Known issues and data caveats

Documented here so reviewers and reusers meet them in the open rather than
discovering them. None of these affect the published MMRI values, and each is
checked by `scripts/verify_repo.py` where it can be.

## 1. Citation drift in a small number of cells

The scoring prompt asks the model to cite the `chunk_id` of every evidence chunk
it relied on. In a small residue of cells, a cited id is not among the chunks
actually retrieved for that cell:

| Model | Unresolved citations | Cells affected |
|---|---|---|
| Claude | 7 / 495 (1.41%) | 3 / 120 |
| GPT | 5 / 386 (1.30%) | 1 / 120 |

All affected Claude cells are in `ANZ_2021_ESGSupplement`. Of the 7 ids, 6 exist
elsewhere in that report — the model cited a neighbouring chunk it had seen in an
adjacent position — and 1 (`chunk_0243`) does not exist at all.

**Impact on results: none.** P/S/Q scores are the model's judgment of the
evidence it was shown; the citation list is an audit aid, not an input to the
score. The evidence actually presented for every cell is fully recorded in
`data/retrieved_evidence.csv`, so any cell can be re-examined independently of
what the model cited.

`verify_repo.py` reports this as a rate against a documented 2% ceiling rather
than as a pass/fail, so a future re-scoring run that drifts materially worse
will surface.

## 2. MMRI level is model-dependent

Claude and GPT, given an identical corpus, identical retrieval and an identical
prompt, produce very different absolute levels — mean MMRI 0.172 vs 0.464 — and
agree only moderately per report (Pearson r = 0.578).

Treat MMRI as a **comparative** instrument within a single model, not as an
absolute score comparable across models. Reported in `data/model_comparison.csv`
and discussed in the paper.

## 3. Human comparison is limited in scope

`data/human_annotations.csv` holds 30 report–topic pairs assessed by **one**
annotator. That provides an initial reference for human–model correspondence;
it does **not** support an inter-annotator reliability claim, and it is not a
validation of the index.

Correspondence on fine-grained intensity is modest (Pearson r ≈ 0.23–0.40 by
dimension; Cohen's κ = 0.47 on binarised Presence), and the annotator scored
lower than the model on the soft-governance topics — financial inclusion, ESG in
credit analysis and systemic risk — by 0.5 coverage points on average. Full
statistics in `results/robustness/human_agreement_metrics.csv`.

This is a real limitation of the study, not a defect in the data.

## 4. Re-scoring will not reproduce the released scores exactly

Stage 2 calls an LLM, so it is not deterministic. Across 3 repeat runs the
per-report MMRI standard deviation averages 0.033
(`results/robustness/stability_kruns_summary.csv`).

Stages 1.1, 1.2 and 3 *are* deterministic: given the same PDFs you will get the
same chunks, the same retrieved evidence and — from the released scores — the
same MMRI and figures.

To reproduce the published numbers, use the released scores in `results/`.

## 5. `retrieved_evidence.csv` has 568 rows, not 600

Retrieval returns **up to** 5 chunks per cell, so the ceiling is 120 × 5 = 600.
The actual composition:

| | Cells |
|---|---|
| Returned the full 5 chunks | 109 |
| Returned 1–4 chunks | 9 |
| Returned no chunks at all | 2 |

Retrieval runs over every cell including the 18 where `a_i = 0`, so
inapplicable cells still carry evidence — applicability is applied at
aggregation, not at retrieval.

A short chunk list means the report contained little matching material, which is
itself a signal: it generally accompanies low Presence. The two empty cells are
the extreme of that case.

## 6. OCR was applied to a small number of pages

Some report pages are image-only and were OCR'd during extraction at 200 DPI.
Per-report OCR page counts are in `data/report_metadata.csv` (`n_ocr_pages`) and
per-cell counts in `data/coverage_scores.csv` (`n_ocr_chunks`). OCR text can
carry recognition errors; the counts let you check whether any particular result
leans on OCR'd material.

## 7. Extraction can interleave multi-column text

The extractor works from the PDF text layer. On some multi-column layouts this
interleaves text from adjacent columns within a chunk, which is visible in a few
`text` values in `data/retrieved_evidence.csv`. The scoring models were shown
this same text, so it is released exactly as scored rather than cleaned after the
fact.
