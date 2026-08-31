# Anonymous Zenodo deposit — step by step

Goal: a citable DOI you can put in the anonymized manuscript **without**
revealing authorship, then update to named authors after acceptance.

This has to be done from your own Zenodo account. The archive is already built:

```
/Users/mingqin/Downloads/MMRI-ESG-Banking-v1.0.0.zip     (2.1 MB, 331 files)
```

Rebuild it any time with:

```bash
cd /Users/mingqin/Downloads/MMRI-ESG-Banking
git archive --format=zip --prefix=MMRI-ESG-Banking-v1.0.0/ \
  -o /Users/mingqin/Downloads/MMRI-ESG-Banking-v1.0.0.zip HEAD
```

## Before you upload

Fill in the 20 `source_url` and `access_date` fields in
`data/report_metadata.csv` (see `docs/CORPUS.md`), commit, and rebuild the
archive. A DOI is permanent; the first deposit should be complete.

Then confirm everything still passes:

```bash
python3 scripts/verify_repo.py        # expect 21/21
python3 scripts/fetch_reports.py      # expect 20 verified
```

## Do not connect the GitHub integration

Zenodo's GitHub integration would name the repository — and therefore your
account — in the deposit record. **Upload the ZIP manually instead.** Link the
repository after acceptance, in a new version.

## Deposit metadata

At <https://zenodo.org/uploads/new>, upload the ZIP and set:

| Field | Value |
|---|---|
| Resource type | Dataset (or *Software* if you prefer the code emphasis) |
| Title | Research data and reproducibility materials for a benchmark-based, LLM-assisted assessment of ESG disclosure-materiality misalignment in commercial banking |
| Authors | See below — **do not use your real name yet** |
| Description | See below |
| License | Creative Commons Attribution 4.0 International |
| Version | 1.0.0 |
| Keywords | ESG disclosure; materiality; SASB; commercial banking; large language models; sustainability reporting; reproducibility |

### Authors field, during review

Zenodo requires at least one creator. Use an institutional or withheld
placeholder rather than your name:

```
Name:        Anonymous (author details withheld for peer review)
Affiliation: (leave blank)
```

Zenodo permits this; the record can be edited to named authors later without
changing the DOI.

### Description, during review

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

## Reserving the DOI

Zenodo lets you **reserve a DOI before publishing** — use it. On the upload
form, click *Reserve DOI*, put that DOI in your manuscript, then publish the
deposit when you submit.

## The statement for the anonymized manuscript

```latex
\section*{Data and code availability}

The derived research data and analysis code supporting this study are openly
available at \url{https://doi.org/[RESERVED DOI]}. The deposit contains the
corpus manifest with source URLs and SHA-256 checksums for all 20 reports, the
six SASB FN-CB topic definitions, the retrieved evidence shown to the models,
all per-cell Presence/Specificity/Quantification scores with model rationales
and evidence citations for both models, the coverage, misalignment,
applicability and index values, the exact scoring prompt, the weighting, prompt
and repeat-run robustness outputs, the 30 human-assessed report--topic pairs,
and the scripts that generate every table and figure in this paper.

The 20 source sustainability reports are published by the respective banks and
are not redistributed, as they remain those institutions' copyright. The deposit
records a direct source URL, access date and SHA-256 checksum for each, together
with a script that re-downloads the corpus and verifies it byte-for-byte, so the
exact documents analysed here can be reconstructed and confirmed.
```

Note this cites the DOI only — no GitHub URL, no personal domain.

## After acceptance

1. Edit the Zenodo record: replace the placeholder creator with the real author
   list and ORCIDs. The DOI does not change.
2. Add the journal reference to the record.
3. Make the GitHub repository public again:
   ```bash
   gh repo edit Inspiring-Ming/Quantifying-Materiality-Misalignment-Risk- \
     --visibility public --accept-visibility-change-consequences
   ```
   GitHub Pages resumes automatically; the site returns at its old URL.
4. Restore the journal name and full citation in `README.md`,
   `CITATION.cff`, and the site footer in `docs/index.html`.
5. Optionally publish a new Zenodo version linked to the public repository.

## CRediT and the title page

Keep author names and CRediT contribution statements **out of the anonymized
manuscript**. Put them on the separate title page, or in the submission system's
metadata fields, per the journal's double-anonymized guidance. The full CRediT
statement goes into the production manuscript after acceptance.
