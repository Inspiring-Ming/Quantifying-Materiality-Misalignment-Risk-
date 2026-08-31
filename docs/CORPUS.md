# The 20-report corpus

## Selection rule

One report per (bank, year), 2021–2025, from the **Australian parent entity**
(ANZ Group, CBA, NAB, Westpac Group). NZ subsidiaries and other affiliates are
out of scope.

For each bank in each year we take the primary ESG/sustainability-focused
publication at AU-parent level, in this priority order:

1. Standalone ESG Report or Sustainability Report / Supplement / Appendix.
2. Failing that, the bank's Climate Report or the sustainability section of the
   Annual Report.

The rule is applied bank-by-bank against what the bank actually published. We
never substitute a document from a different year or entity.

## What each bank published

| Bank | Pattern across 2021–2025 |
|---|---|
| **ANZ** | ESG Supplement each year; renamed ESG Report in 2025 (same publication line) |
| **CBA** | 2021 has no standalone sustainability document, so the Annual Report's sustainability section is used; Sustainability Appendix / Sustainability Reporting thereafter |
| **NAB** | 2021 Annual Review; Climate Report 2022–2025. NAB publishes no standalone Sustainability/ESG report at AU-parent level. Its Sustainability Data Pack is `.xlsx` only and is not part of the PDF corpus |
| **Westpac** | Sustainability Supplement 2021–2022; Climate Report 2023–2024 (no standalone AU-parent Sustainability Report those years); Sustainability Report 2025 |

## Climate-only reports and the applicability indicator

Six reports are climate-focused rather than full-scope sustainability reports:

- NAB 2022, 2023, 2024, 2025
- Westpac 2023, 2024

A climate report is not expected to cover data security, financial inclusion or
business ethics. Scoring it as though it should would confuse *publication scope*
with *disclosure quality*. These reports therefore carry `a_i = 0` on those three
topics, and their MMRI is computed over the three in-scope topics only.

They are flagged `climate_only = 1` in `data/report_metadata.csv`.
`scripts/verify_repo.py` asserts that the `a_i = 0` cells in the score tables
line up exactly with that flag.

## Filling in `source_url` and `access_date`

**These two columns ship empty and must be completed before deposit.**

Everything else in `data/report_metadata.csv` is derived mechanically from the
extraction manifest and the PDF bytes, so it cannot drift. The URLs are the one
thing that has to be recorded by hand — and a wrong URL in a data availability
statement is worse than a blank one, so they are deliberately left for the
authors to verify rather than guessed.

For each of the 20 rows:

1. Find the report on the bank's own investor-centre or sustainability page.
   Prefer a stable, bank-hosted URL over a CDN or search-result link.
2. Put the direct PDF link in `source_url`.
3. Put the date you retrieved it in `access_date`, ISO 8601 (`2025-04-18`).
4. Confirm you have the right file:

```bash
python3 scripts/fetch_reports.py --out /tmp/corpus_check
```

Every row should report `OK`. A `MISMATCH` means the URL serves a different
file from the one that was scored — usually a silently re-published version.
Note it in `docs/KNOWN_ISSUES.md` rather than changing the recorded checksum:
the checksum documents what was actually analysed.

Bank investor-centre landing pages, as a starting point:

- ANZ — anz.com → About us → ESG / Sustainability reporting
- CBA — commbank.com.au → About us → Investors → Annual reporting
- NAB — nab.com.au → About us → Investor centre → Annual reporting
- Westpac — westpac.com.au → About us → Sustainability → Reporting

## Known scope limitations

- **Annual Report financial notes are out of scope.** Some SASB metrics live in
  the Annual Report's financial statements — FN-CB-510a.1 (monetary losses from
  legal proceedings) and FN-CB-550a.1 (G-SIB indicators, capital ratios). These
  generally sit outside the sustainability publications that form this corpus,
  so they read as absent. This is the "Annual-Report-scope" restriction in the
  paper's limitations section.
- **Supplementary data packs are excluded.** Several banks publish a
  Sustainability Data Pack (Excel) with detailed SASB tables. These are not part
  of the PDF corpus. Where a report points to one ("see the 2025 Sustainability
  Data Pack for breach counts"), the scoring model correctly treats that as an
  external pointer, not as in-corpus evidence — which lowers Quantification.
  This is deliberate: MMRI measures what the *report* discloses.
