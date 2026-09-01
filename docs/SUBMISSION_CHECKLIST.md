# Data availability: the whole process, start to finish

Four steps, roughly 45 minutes. Step 1 is the only slow one.

---

## Step 1 — Fill in the 20 source URLs (~30 min)

The only information that cannot be derived from files on disk.

```bash
cd /Users/mingqin/Downloads/MMRI-ESG-Banking
python3 scripts/build_url_sheet.py
```

That writes `url_sheet.csv` — 20 rows, two columns to fill. Open it in Excel or
Numbers. For each row:

1. Go to the bank landing page in the `bank_landing_page` column.
2. Find the report matching `report_title`. The `pdf_title` column holds the
   title the publisher embedded in the file itself, so you can confirm you have
   the right document — e.g. CBA 2023 should read
   *"2023 Sustainability Reporting (pages 18-39 of Annual Report)"*.
3. Copy the direct PDF link into `source_url`. Prefer a bank-hosted URL over a
   CDN or search-result link.
4. Put today's date in `access_date` as `YYYY-MM-DD`.

Then merge it back:

```bash
python3 scripts/build_url_sheet.py --merge
```

The merge refuses to run on a URL that isn't `https://`, a malformed or future
date, or a blank row — it tells you which rows to fix. It only ever touches
those two columns; every checksum and count stays as generated.

Then confirm the URLs really serve the documents you scored:

```bash
python3 scripts/fetch_reports.py --out /tmp/corpus_check
```

Every row should say `OK`. `MISMATCH` means that URL serves a *different* file
from the one analysed — usually a silently re-published version. Note it in
`docs/KNOWN_ISSUES.md` rather than editing the recorded checksum: the checksum
documents what was actually analysed.

```bash
python3 scripts/verify_repo.py        # expect 21/21, and no blank-URL note
```

---

## Step 2 — Build the anonymized package (~1 min)

Do **not** deposit the working repository. Its README and project page carry the
GitHub account name, which would identify you to reviewers. Build the anonymized
copy instead:

```bash
git add -A && git commit -m "Add source URLs and access dates for the corpus"
python3 scripts/build_review_package.py
```

This copies the research package, rewrites the README for anonymous review, sets
the licence and citation metadata to withheld, drops the project site and the
internal workflow notes, and then **refuses to produce the archive** if any
identifying string survives. It builds from the working tree, so no git history
is carried across.

Output: `review-package.zip` (~1.1 MB). Verify it yourself before uploading:

```bash
grep -ri "inspiring-ming\|mingqin\|github" review-package/   # expect no matches
```

All data, results, prompts, figures, scripts, and the data dictionary, corpus,
environment and known-issues notes are kept unchanged. The package still passes
its own self-check:

```bash
cd review-package && python3 scripts/verify_repo.py   # expect 21/21
```

---

## Step 3 — Zenodo (~10 min)

Sign in at <https://zenodo.org> (ORCID or GitHub login both work), then
**New upload**.

**Upload `review-package.zip` by drag-and-drop. Do not connect the GitHub integration** — it
would name the repository, and therefore your account, in a record that is meant
to be anonymous during review. Link the repository after acceptance.

Fill in:

| Field | Value |
|---|---|
| Resource type | **Dataset** |
| Title | Research data and reproducibility materials for a benchmark-based, LLM-assisted assessment of ESG disclosure-materiality misalignment in commercial banking |
| Creators | `Anonymous (author details withheld for peer review)` — no affiliation |
| Version | `1.0.0` |
| License | **Creative Commons Attribution 4.0 International** |
| Keywords | ESG disclosure; materiality; SASB; commercial banking; large language models; sustainability reporting; reproducibility |

Description — paste this:

> Research data and reproducibility materials accompanying a manuscript
> currently under double-anonymized peer review. Author and venue details are
> withheld until publication.
>
> The package supports a benchmark-based, LLM-assisted measure of the gap
> between what a bank's sustainability report discloses and what the SASB FN-CB
> Commercial Banks standard treats as material, applied to 20 sustainability
> reports from four major Australian banks over 2021–2025.
>
> Contents: the corpus manifest with source URLs, access dates and SHA-256
> checksums for all 20 reports; the six SASB FN-CB topic definitions; 568
> retrieved evidence chunks; 120 report–topic assessments per model across two
> models, with per-dimension rationales and evidence citations; coverage,
> misalignment, applicability and index values; the exact scoring prompt;
> weighting, prompt-structure and repeat-run robustness outputs; 30
> human-assessed pairs; and the scripts that generate every table and figure.
>
> The 20 source reports are published by the respective banks and are not
> redistributed here, as they remain those institutions' copyright. The package
> records a source URL, access date and SHA-256 checksum for each, together with
> a script that re-downloads the corpus and verifies it byte-for-byte.

Then click **Reserve DOI**. You now have a DOI to cite. **Publish the deposit
when you submit the manuscript** — a reserved-but-unpublished DOI does not
resolve, and a reviewer clicking a dead link is worse than no link at all.

---

## Step 4 — Put it in the submission (~5 min)

Two places, both needed.

### 4a. In the manuscript

Replace the existing `\section*{Data and code availability}` with:

```latex
\section*{Data and code availability}

The derived research data and analysis code supporting this study are openly
available at \url{https://doi.org/10.5281/zenodo.XXXXXXX}. The deposit contains
the corpus manifest with source URLs and SHA-256 checksums for all 20 reports,
the six SASB FN-CB topic definitions, the retrieved evidence shown to the
models, all per-cell Presence/Specificity/Quantification scores with model
rationales and evidence citations for both models, the coverage, misalignment,
applicability and index values, the exact scoring prompt, the weighting, prompt
and repeat-run robustness outputs, the 30 human-assessed report--topic pairs,
and the scripts that generate every table and figure in this paper.

The 20 source sustainability reports are published by the respective banks and
are not redistributed, as they remain those institutions' copyright. The deposit
records a direct source URL, access date and SHA-256 checksum for each, together
with a script that re-downloads the corpus and verifies it byte-for-byte, so the
exact documents analysed here can be reconstructed and confirmed.
```

DOI only. No GitHub URL, no personal domain.

### 4b. In the submission system

At the Data Statement step, choose the option for **data in a public
repository** (not "available on request" — that is what created the original
inconsistency), and paste:

> The derived research data and analysis code supporting this study are openly
> available at https://doi.org/10.5281/zenodo.XXXXXXX. The deposit contains the
> corpus manifest with source URLs and SHA-256 checksums for all 20 reports, the
> SASB FN-CB topic definitions, the retrieved evidence, all per-cell scores with
> model rationales and citations for both models, the index values, the exact
> prompts, all robustness and human-comparison outputs, and the scripts
> generating every table and figure. The source sustainability reports are not
> redistributed as they remain the publishing banks' copyright; the deposit
> records a URL, access date and checksum for each, plus a script to re-download
> and verify them.

---

## Also check before submitting

- [ ] No author names or CRediT statements in the manuscript body — title page
      or submission metadata only
- [ ] No `github.com` or `inspiring-ming.github.io` URL anywhere in the manuscript
- [ ] The GitHub repository is still **private** (it is; re-check if unsure)
- [ ] Acknowledgements and funding statements are anonymized
- [ ] No working directory names (`Claude model experiment/`,
      `GPT model expriements/`) left in the methods

## After acceptance

1. Edit the Zenodo record: real authors and ORCIDs. The DOI does not change.
2. `gh repo edit ... --visibility public` — Pages resumes, the site returns.
3. Restore the journal name and full citation in `README.md`, `CITATION.cff`
   and the site footer.
4. Add the full CRediT statement to the production manuscript.
