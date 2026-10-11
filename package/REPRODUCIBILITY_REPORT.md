# Reproducibility report (R40 archive)

Scope: what was checked in this archiving pass, with results. Nothing was recomputed from raw satellite data.

## Evidence classes
- **A. Re-derived and identical:** tables recomputed by the journal-edition code from the first package compared with the first-package tables: 7 of 7 IDENTICAL (journal_docs_and_tables/tables/consistency_vs_source_package.csv).
- **B. Integrity-checked files:** r40-results/sha256.txt lists 194 files and all 194 match the committed files (SHA-256); the two unlisted files are sha256.txt and run_console.log. r40-cartography-results/reuse_integrity_check.csv: 102 of 102 reused rasters MATCH.
- **C. Traced to stored CSV:** the manuscript numbers listed below equal the values in the stored CSV tables; the computations behind them were not re-run here.
- **D. Limited independent verification:** Kazakhstan has no lidar DTM; ATL08 gives 1-D along-track samples only; DEM agreement is not accuracy.

## Manuscript-to-table trace (candidate of 11 Oct 2026)
| Manuscript item | Source file (branch) | Result |
|---|---|---|
| Table 1 pooled AURC (9 values), CIs in 5.1 | tables/extra_paired_bootstrap.csv (r40-extra) | match |
| Table 2 leave-one-country-out AURC (12 values) | tables/extra_leave_one_country_out_aurc.csv (r40-extra) | match |
| Table 4 ATL08 AURC (18 values), counts 897 / 4,825 | tables/icesat2_riskcov_aurc.csv (r40-icesat2-riskcov) | match |
| Table 3 Kok-Zhailau shares, 683 and 348 px | tables/decisions_by_site.csv (r40-results), mask functional_footprint_derived | match |
| ATL08 pairs 902, bias -0.31, MAE 1.34, RMSE 2.43, NMAD 1.26 | tables/icesat2_alongtrack_slope_vs_dem.csv (r40-icesat2) | match |
| Operating points: 96.1 % / 0.93 %, 91.5 % / 1.36 %, 91.4 % / 5.12 % | tables/icesat2_riskcov_operating_points.csv | match |
| Stress errors 4.9, 5.9, 8.8, 3.3, 2.6, 9.8, 9.2, 6.0 % at 15 deg | tables/validation_stress_tests.csv (r40-results) | match |
| 49,162 / 7,018 / 1,484 ATL08 segments | journal tables/journal_figure_shares_as_drawn.csv | match |
| Overlap difference 2.19 m (mean 0.29 m) | journal_exceptions_report.md | match |

Not traced in this pass: the 12-of-12 site x threshold claim, operating-point counts 1/4, 3/4, 2/4 (file extra_leave_one_country_out_operating.csv exists), ECE values per site, ATL08-vs-lidar RMSE range 0.94-2.06 deg.

## Code
- Unit tests, branch r40-cartography (63d9dbf): 34 run, 33 pass, 1 error (test_timeseries.test_grid: module pyproj not installed in the archiving environment). The 33 passing tests cover core, extra, ICESat-2 and journal-library code. The workflow runs 38084018547 and earlier successful runs completed with their test steps; logs were not readable from this environment.
- Workflow runs (INVENTORY_GITHUB_ACTIONS_RUNS.csv): 30 runs listed; 5 earlier runs failed and were followed by fixed successful runs of the same workflow.

## Separation of evidence (kept as in the manuscript)
1. Lidar validation: Switzerland (swissALTI3D) and United States (3DEP), four sites, leave-one-site-out and leave-one-country-out.
2. ICESat-2 ATL08: along-track slope pairs, auxiliary reference with a noise floor.
3. Kazakhstan: transferred decisions; error not measured; no independent DTM.

## Open limitations
Repository has no LICENSE file. Stage outputs R29-R39 are not in the repository. HyP3/Sentinel-1/-2 stages are archived but not used in manuscript results. The cartography code commits show GitHub "Unverified" (author email); history was not rewritten.
