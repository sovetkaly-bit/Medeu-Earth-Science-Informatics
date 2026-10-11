# R40 archive: Support-Aware Terrain Threshold Decisions (version 1.0.0, prepared 2026-10-11)

Prepared as a Zenodo deposit; **not yet submitted or published**. No DOI exists.

## Files (logical archives)
| File | Content |
|---|---|
| R40_git_history.bundle | complete git history of 17 branches (everything except the large r40-cartography-sources branch), `git clone R40_git_history.bundle` |
| R40_code_main_11d7ab6.zip | code, workflows and tests at main (11d7ab6) |
| R40_code_cartography_63d9dbf.zip | code at branch r40-cartography, commit 63d9dbf (journal map code) |
| R40_results_run38058021115.zip | primary results of run 38058021115 (tables, figures, derived rasters, boundaries, sha256.txt) |
| R40_stage_outputs.zip | outputs of r40-extra, r40-icesat2, r40-icesat2-riskcov, r40-context, r40-hyp3-collect, r40-cartography-results |
| R40_JOURNAL_FIGURES_part01..05_of_05.zip | **final journal figures A-E** (PNG 300 dpi, PDF, SVG) + A4 proofs (code commit 63d9dbf, run 38084018547) |
| R40_SOURCE_GEODATA_part01..04_of_04.zip | redistributable source geodata and editable files for the figures |
| R40_JOURNAL_PARTS_INDEX.csv | size and SHA-256 of the 9 journal/geodata parts |
| R40_journal_docs_and_tables.zip | captions, README, exceptions report, manifest_journal.csv, consistency and readability tables |
| docs: README_ZENODO.md, LICENSES_REPORT.md, REPRODUCIBILITY_REPORT.md, DATA_AND_CODE_AVAILABILITY_EN.md, zenodo_metadata.json, MANIFEST_ARCHIVE_FILES.csv, MANIFEST_MEMBERS.csv, INVENTORY_* | documentation and inventories |

## Final results used by the manuscript
Tables 1-4 come from r40-extra (run 38074462352) and r40-icesat2-riskcov (run 38071303684) and r40-results (run 38058021115). Final maps: R40_JOURNAL_FIGURES (run 38084018547). Earlier first-edition previews (1500 px, r40-cartography-results) are kept as history and are superseded.

## Not included
R29-R39 stage files are not in the GitHub repository (they exist in the author storage, see INVENTORY_EARLIER_STAGES_NOT_IN_ARCHIVE.csv). Manuscript and review documents, ALOS AW3D30 / FABDEM rasters, KazEOSat imagery, tokens and personal data are not included.

## Verify
`sha256sum -c` against MANIFEST_ARCHIVE_FILES.csv (column sha256). Reproduce: GitHub Actions workflows in `.github/workflows` (r40_kz_all_sources.yml, r40_icesat2.yml, r40_icesat2_riskcov.yml, r40_extra.yml, r40_cartography.yml, r40_cartography_journal.yml).
