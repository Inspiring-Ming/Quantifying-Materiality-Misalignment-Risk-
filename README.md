# MMRI-ESG-Banking

Reproducibility materials for **"[PAPER TITLE]"**, submitted to *Technological Forecasting & Social Change*.

**Project page → https://inspiring-ming.github.io/Quantifying-Materiality-Misalignment-Risk-/**

This repository contains the derived research data, model outputs, prompts, and
analysis code behind the Materiality Misalignment Risk Index (MMRI): a
benchmark-based, LLM-assisted measure of the gap between what a bank's
sustainability report discloses and what the SASB FN-CB Commercial Banks
standard treats as material.

**Study at a glance** — 20 sustainability reports from the four major Australian
banks (ANZ, CBA, NAB, Westpac), 2021–2025, scored against 6 SASB FN-CB topics on
3 dimensions, giving 120 scored cells per model, for 2 models.

| | |
|---|---|
| Corpus | 20 reports · 4 banks · 2021–2025 |
| Benchmark | SASB FN-CB Commercial Banks (2025-12) · 6 topics |
| Scoring | Presence / Specificity / Quantification, 5-point anchors |
| Primary model | Claude (`claude-opus-4-7`) · mean MMRI **0.172** |
| Comparator | GPT (`gpt-5.4-mini`) · mean MMRI **0.464** |
| Robustness | weight ablation · prompt ablation · 3-run stability · 30-cell human validation |

## Citation

> [AUTHORS] ([YEAR]). *[PAPER TITLE]*. Technological Forecasting & Social Change. DOI: [ARTICLE DOI]

Archived release of this repository: **DOI [ZENODO DOI]**

## A note on the source PDFs

**The 20 source PDFs are not redistributed here.** They are published free of
charge by each bank but remain the banks' copyright, and this repository is not
the right vehicle to republish them.

Reproducibility does not depend on that. `data/report_metadata.csv` records the
`source_url` and a **SHA-256 checksum** for every report, so you can re-download
the corpus and verify byte-for-byte that you hold the same documents that
produced the published scores:

```bash
python3 scripts/fetch_reports.py     # download into reports/, then verify
```

If a checksum no longer matches, the bank has re-published that PDF at the same
URL. The scores here describe the version whose checksum is recorded.

Everything downstream of the PDFs — extracted evidence, scores, rationales,
citations, MMRI — **is** in this repository, so all analysis after the extraction
step can be rerun without downloading anything.

## Layout

```
MMRI-ESG-Banking/
├── data/                        Analysis-ready tables (start here)
│   ├── report_metadata.csv        20 reports: title, URL, SHA-256, page/chunk counts
│   ├── sasb_topics.csv            6 SASB FN-CB topics: summaries, metrics, keywords
│   ├── retrieved_evidence.csv     568 evidence chunks shown to the models
│   ├── coverage_scores.csv        120 Claude cells: P/S/Q, coverage, misalignment, a_i
│   ├── coverage_scores_gpt.csv    120 GPT cells, same schema
│   ├── mmri_results.csv           MMRI per report (primary study)
│   ├── model_comparison.csv       Claude vs GPT MMRI, per report
│   └── human_annotations.csv      30 human-scored cells paired with Claude
│
├── prompts/
│   ├── scoring_prompt_v2.md       The exact scoring prompt (both models)
│   └── sasb_fncb_topics.json      Machine-readable topic schema
│
├── scripts/
│   ├── fetch_reports.py           Re-download + checksum the corpus
│   ├── verify_repo.py             Self-check; reproduces the headline numbers
│   ├── extraction/                Stage 1.1 PDF → chunks, 1.2 topic retrieval
│   ├── scoring/                   Stage 2 LLM scoring
│   ├── mmri/                      Stage 3 MMRI + main figures
│   ├── robustness/                Ablations, stability, human agreement
│   └── figures/                   Framework and comparison figures
│
├── results/
│   ├── claude/                    120 per-cell responses, audit log, scores
│   ├── gpt/                       120 per-cell responses, scores
│   └── robustness/                Ablation, stability, agreement outputs
│
├── figures/                       The 11 figures as they appear in the paper
└── docs/                          Data dictionary, corpus notes, known issues
```

## Reproducing the results

Requires Python 3.10+.

```bash
pip install -r requirements.txt

# Confirm the repository is internally consistent and matches the paper
python3 scripts/verify_repo.py
```

`verify_repo.py` checks structure, recomputes coverage and misalignment from the
raw P/S/Q scores, confirms every applicability flag, and reproduces the three
headline numbers (Claude mean MMRI 0.172, GPT mean MMRI 0.464, cross-model
r = 0.578).

To rerun the pipeline end to end you also need the PDFs:

```bash
python3 scripts/fetch_reports.py                          # 1. rebuild the corpus
python3 scripts/extraction/stage1_1_extract_chunks.py     # 2. PDF → chunks
python3 scripts/extraction/stage1_2_chunks_per_topic.py   # 3. topic retrieval
python3 scripts/scoring/stage2_score.py show_all          # 4a. render prompts
#                    ... score them with your model of choice ...
python3 scripts/scoring/stage2_score.py collect           # 4b. validate + aggregate
python3 scripts/mmri/stage3_compute_mmri.py               # 5. MMRI + figures
```

Stage 2 is deliberately model-agnostic and does not call an API itself: `show_all`
renders every cell's prompt to stdout, you score them with whatever model or SDK
you choose and write one `.response.json` per cell, and `collect` validates those
and builds the score tables and audit log. That is how the same prompt was run
against both Claude and GPT.

Steps 1–3 and 5 are deterministic. Step 4 is not — re-scoring will not reproduce
the released scores exactly. The observed run-to-run spread is σ_mean = 0.033 per
report over 3 runs (`results/robustness/stability_kruns_summary.csv`). To
reproduce the *published* numbers, use the released scores in `results/`.

Note that the pipeline scripts carry absolute paths from the original working
tree; adjust the `ROOT` constant at the top of each before rerunning.

## How the index works

For report *r* and topic *i*, the model assigns Presence, Specificity and
Quantification on the 5-point scale {0, 0.25, 0.5, 0.75, 1.0}. Coverage is their
mean and misalignment is its complement:

```
C_ri = mean(P, S, Q)          M_ri = 1 − C_ri
```

Report-level MMRI is the applicability-weighted mean of topic misalignment:

```
MMRI_r = Σ_i a_i · w_i · M_ri  /  Σ_i a_i · w_i
```

with equal weights `w_i = 1/6`. The applicability indicator `a_i` is 0 for the
three non-climate topics (data security, financial inclusion, business ethics)
in the six climate-only reports, so those reports are not penalised for omitting
topics their publication scope never covered. Reports flagged this way are marked
`climate_only = 1` in `data/report_metadata.csv`.

Higher MMRI = greater misalignment with the benchmark.

## Interpreting these numbers

Three limits are worth stating plainly, and are discussed in the paper:

- **Absolute MMRI is model-dependent.** Claude and GPT differ substantially in
  level (0.172 vs 0.464) while agreeing only moderately per report (r = 0.578).
  The index is best read comparatively — across reports, banks and years within
  one model — not as an absolute score.
- **Human validation is a pilot, not a reliability study.** 30 cells, one
  annotator. It reports human–model agreement, not inter-rater reliability.
  Agreement on fine-grained intensity is modest (see
  `results/robustness/human_agreement_metrics.csv`).
- **Scope is the published report.** MMRI measures disclosure against the
  benchmark, not the underlying conduct. Metrics a bank reports elsewhere — in
  an Annual Report note or an Excel data pack — count as absent.

See `docs/KNOWN_ISSUES.md` for data-level caveats.

## License

- **Code** (`scripts/`): MIT — see `LICENSE`.
- **Derived data** (`data/`, `results/`): CC BY 4.0 — see `LICENSE-DATA`.
- **Source PDFs**: not included; copyright of the publishing banks.
- **SASB FN-CB standard**: © IFRS Foundation. Topic summaries in
  `data/sasb_topics.csv` and `prompts/sasb_fncb_topics.json` are quoted for
  research purposes; the standard itself is not redistributed.
