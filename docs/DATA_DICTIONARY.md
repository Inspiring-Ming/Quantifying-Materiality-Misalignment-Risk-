# Data dictionary

Every column in `data/`. All files are UTF-8 CSV with a header row; lines
beginning `#` are provenance comments and should be skipped when parsing.

Common keys: `report_id` (e.g. `ANZ_2021_ESGSupplement`) joins every table;
`(report_id, topic)` identifies a scored cell.

---

## `report_metadata.csv` — 20 rows, one per report

| Column | Type | Description |
|---|---|---|
| `report_id` | str | Stable key, `{bank}_{year}_{type}` |
| `bank` | str | ANZ, CBA, NAB, Westpac |
| `bank_legal_name` | str | Full legal entity name |
| `year` | int | Reporting year, 2021–2025 |
| `report_title` | str | Human-readable title |
| `report_type` | str | ESG Supplement, Climate Report, etc. |
| `climate_only` | 0/1 | 1 = climate-focused; drives `a_i = 0` on non-climate topics |
| `pdf_filename` | str | Expected filename in `reports/` |
| `n_pages` | int | Pages in the PDF |
| `n_chunks` | int | Chunks produced by extraction |
| `n_tables_extracted` | int | Structured tables captured |
| `n_ocr_pages` | int | Pages requiring OCR |
| `file_size_bytes` | int | Size of the scored PDF |
| `sha256` | str | SHA-256 of the scored PDF — the provenance anchor |
| `source_url` | str | Direct download URL *(filled in by authors)* |
| `access_date` | date | ISO 8601 retrieval date *(filled in by authors)* |

## `sasb_topics.csv` — 6 rows, one per SASB topic

| Column | Type | Description |
|---|---|---|
| `topic_id` | str | Internal key, e.g. `data_security` |
| `sasb_code_prefix` | str | e.g. `FN-CB-230a` |
| `topic_name` | str | Official SASB topic name |
| `summary` | str | Official SASB topic summary (quoted) |
| `n_metrics` | int | Number of SASB metrics under the topic |
| `metric_codes` | str | `;`-separated metric codes |
| `metric_descriptions` | str | `\|`-separated metric descriptions |
| `keyword_seeds` | str | `;`-separated retrieval seed terms |
| `evidence_required_for_high_score` | str | `\|`-separated scoring rubric anchors |

## `retrieved_evidence.csv` — 568 rows, one per retrieved chunk

The exact evidence each score was based on. See `docs/KNOWN_ISSUES.md` §5 for
why this is 568 and not 600.

| Column | Type | Description |
|---|---|---|
| `report_id`, `topic` | str | The cell this chunk was retrieved for |
| `a_i` | 0/1 | Applicability of this topic to this report |
| `rank` | int | Retrieval rank, 1 = best match |
| `chunk_id` | str | `{report_id}#chunk_NNNN` — referenced by model citations |
| `page` | int | Source page in the PDF |
| `kinds` | str | `;`-separated chunk kinds (`prose`, `table`, `ocr`) |
| `n_words` | int | Word count |
| `kw_hits` | int | Topic keyword-seed matches |
| `retrieval_score` | float | Retrieval ranking score |
| `force_included` | 0/1 | 1 = force-included as SASB-metric-bearing |
| `text` | str | Verbatim extracted text shown to the model |

## `coverage_scores.csv` — 120 rows (Claude) · `coverage_scores_gpt.csv` — 120 rows (GPT)

| Column | Type | Description |
|---|---|---|
| `model` | str | `claude` or `gpt` |
| `report_id`, `topic` | str | Cell identity |
| `presence` | float | P ∈ {0, .25, .5, .75, 1} — is the topic addressed? |
| `specificity` | float | S — how substantive is the disclosure? |
| `quantification` | float | Q — are SASB-mandated numbers given? |
| `coverage` | float | C = mean(P, S, Q) |
| `misalignment` | float | M = 1 − C |
| `a_i` | 0/1 | Applicability indicator |
| `n_evidence_chunks` | int | Chunks shown to the model *(Claude only)* |
| `n_force_metric_chunks` | int | Of those, force-included *(Claude only)* |
| `n_table_chunks` | int | Of those, from tables *(Claude only)* |
| `n_ocr_chunks` | int | Of those, OCR'd *(Claude only)* |

Per-cell rationales and citations: `results/{claude,gpt}/per_cell/` and
`results/claude/audit_log.csv`.

## `mmri_results.csv` — 20 rows

Report-level index, `MMRI_r = Σ a_i w_i M_ri / Σ a_i w_i`, with `w_i = 1/6`.
Higher = more misaligned.

| Column | Type | Description |
|---|---|---|
| `bank`, `year`, `report_id` | | Report identity |
| `n_topics_applicable` | int | Topics with `a_i = 1` (6, or 3 for climate-only) |
| `MMRI` | float | The index |
| `cov_{topic}` × 6 | float | Per-topic coverage C. Misalignment is `1 − cov` |
| `ai_{topic}` × 6 | 0/1 | Per-topic applicability indicator |

Note the per-topic columns hold **coverage**, not misalignment; the index is
computed from `1 − cov`.

## `model_comparison.csv` — 20 rows

| Column | Type | Description |
|---|---|---|
| `report_id`, `bank`, `year` | | Report identity |
| `mmri_claude` | float | MMRI under Claude |
| `mmri_gpt` | float | MMRI under GPT |
| `difference_gpt_minus_claude` | float | Positive = GPT scored more misaligned |

## `human_annotations.csv` — 30 rows

Pilot validation. One annotator, so this measures human–model agreement, **not**
inter-rater reliability.

| Column | Type | Description |
|---|---|---|
| `cell_idx` | int | Annotation sequence number |
| `report_id`, `topic` | str | Cell identity |
| `human_presence` / `_specificity` / `_quantification` | float | Annotator P/S/Q |
| `human_coverage` | float | Mean of the annotator's three scores |
| `claude_presence` / `_specificity` / `_quantification` | float | Model's scores, same cell |
| `claude_coverage` | float | Model coverage |
| `diff_coverage_human_minus_claude` | float | Negative = annotator scored lower |
| `annotator_notes` | str | Free text; `Uncertain` flags a low-confidence call |

Aggregate statistics: `results/robustness/human_agreement_metrics.csv`.
