# Data availability statement — replacement text

The current statement in `paper.tex` is internally inconsistent: it says the data
are "available on request" and then describes "the repository". It also points at
working directory names (`Claude model experiment/`, `GPT model expriements/`)
that mean nothing to a reader outside the project. TFSC asks that research data
be deposited in a suitable repository and cited from the paper.

Replace the existing `\section*{Data and code availability}` body with the
version below once the Zenodo DOI is minted.

---

## LaTeX (drop-in replacement)

```latex
\section*{Data and code availability}

The derived research data and analysis code supporting this study are openly
available in the \texttt{MMRI-ESG-Banking} repository, archived at Zenodo:
\url{https://doi.org/[ZENODO DOI]} (development version:
\url{https://github.com/[USER]/MMRI-ESG-Banking}). The repository contains the
corpus manifest with source URLs and SHA-256 checksums for all 20 reports, the
six SASB FN-CB topic definitions, the 568 retrieved evidence chunks shown to the
models, all 120 per-cell Presence/Specificity/Quantification scores with model
rationales and evidence citations for both Claude and GPT, the coverage,
misalignment, applicability and MMRI values, the exact scoring prompt, the
weight, prompt and repeat-run robustness outputs, the 30 human validation
annotations, and the scripts that generate every table and figure in this paper.

The 20 source sustainability reports are published by the respective banks and
are not redistributed, as they remain those institutions' copyright. The
repository records a direct source URL, access date and SHA-256 checksum for
each, together with a script that re-downloads the corpus and verifies it
byte-for-byte against those checksums, so the exact documents analysed here can
be reconstructed and confirmed.
```

## Plain text (for a submission form)

> The derived research data and analysis code supporting this study are openly
> available in the MMRI-ESG-Banking repository at https://doi.org/[ZENODO DOI].
> The repository contains the corpus manifest with source URLs and SHA-256
> checksums for all 20 reports, the SASB FN-CB topic definitions, the retrieved
> evidence, all per-cell scores with model rationales and citations for both
> models, the MMRI values, the exact prompts, all robustness and human-validation
> outputs, and the scripts generating every table and figure. The source
> sustainability reports are not redistributed as they remain the publishing
> banks' copyright; the repository records a URL, access date and checksum for
> each, plus a script to re-download and verify them.

---

## Also worth updating

**1. Methods — point at the repository, not at working directories.**
Anywhere the paper refers to `Claude model experiment/`, `GPT model expriements/`
or `pipeline/`, use the published paths instead (`results/claude/`,
`results/gpt/`, `scripts/`). The old names — including the `expriements`
typo — should not appear in the submitted manuscript.

**2. Consider a short reproducibility note in the methods.**

> All scores, rationales and evidence citations are released with the
> repository, so any individual scoring decision reported here can be traced to
> the specific report text it was based on.

That is a genuine strength of this study's design and is currently understated.

**3. Cite the repository in the reference list**, not only in the availability
statement, so the deposit is indexed:

```latex
\bibitem{repo}
[AUTHORS].
\emph{MMRI-ESG-Banking: reproducibility materials for benchmark-based
LLM-assisted ESG disclosure-materiality assessment}.
Zenodo, [YEAR]. \url{https://doi.org/[ZENODO DOI]}
```

## Before you submit

- [ ] Fill `source_url` and `access_date` for all 20 rows (`docs/CORPUS.md`)
- [ ] Run `python3 scripts/fetch_reports.py` — all 20 should verify OK
- [ ] Run `python3 scripts/verify_repo.py` — all checks should pass
- [ ] Replace `[AUTHORS]`, `[PAPER TITLE]`, `[YEAR]` in README, LICENSE, LICENSE-DATA
- [ ] Push to GitHub, create a release, link the Zenodo integration
- [ ] Substitute the minted `[ZENODO DOI]` in the statement above and in README
