# R40 journal figures and editable cartographic sources

Generated 2026-10-10T20:31:55+00:00 | code commit 63d9dbfd55c3d43aeaf3bad527aa03907a0c3a01 | workflow run 38084018547
Based on the first package R40_CARTOGRAPHY_SOURCE_PACKAGE (workflow run 38078170104, artifact 11679378949). Scientific content is unchanged.

## What changed (presentation only)
* Figure width 180 mm (full-width journal figure); every text object >= 7 pt: smallest text over all figures = 7.5 pt (13 of 13 figures pass; tables/a4_readability_audit.csv, tables/font_audit_all_text.csv).
* Captions are NOT inside the images any more: captions_journal.md has a short caption and technical notes per figure.
* One light legend per figure; polygon definitions, windows and CRS are in the captions. Panel titles carry the UTM zone; grid convergence and scale-bar lengths are in tables/map_furniture_parameters.csv.
* Relief: Copernicus GLO-30 DSM, bicubic-resampled (2x overview, 3x windows) FOR DISPLAY ONLY, multi-directional hillshade (azimuth 225, 270, 315, 360 deg, altitude 40 deg), hypsometric tint on the overview. Analysis values stay on the packaged 30 m grid.
* One new real input: Copernicus GLO-30 for the whole 76.85-77.20E, 43.05-43.25N window (inputs_extra/overview_kz; same product and pipeline as the study windows) so the overview has no grey gaps.
* Class colours (Okabe-Ito), class definitions, outlines, numbers: unchanged. tables/consistency_vs_source_package.csv compares the re-derived tables with the first package.

## Folders
* figures/ - R40_Fig_A ... E as PNG (300 dpi), PDF (TrueType text), SVG (text kept as text, relief embedded). A4_proof_pages_100pct.pdf - each figure + caption on an A4 page at 100 %.
* basemaps/ - georeferenced relief rasters (grey hillshade per site, colour RGBA overview) for re-styling in QGIS/Illustrator.
* tables/ - consistency checks, A4 audit, furniture parameters, shares as drawn.
* inputs_extra/ - the new overview DEM and its provenance. scripts/ - code; manifest_journal.csv - every file with source, CRS, licence, SHA-256.

## Editing
* SVG: open in Inkscape/Illustrator; install DejaVu Sans (or replace the font consistently). Text is live text; relief is an embedded image; outlines/graticule/scale bar are paths.
* Georeferenced re-styling: load basemaps/*.tif and derived/vector/*.gpkg (package part with the first edition's vector layers) in QGIS; the decision rasters are in the first package (inputs/rasters/*/decision_combined_t*_risk2.tif).

## Licences
Copernicus GLO-30 ("Contains modified Copernicus data"), NASADEM (public domain), OpenStreetMap contributors (ODbL), Natural Earth (public domain), swissALTI3D (swisstopo OGD), USGS 3DEP (public domain), NASA ICESat-2 ATL08 v007. Not included: ALOS AW3D30, FABDEM (licence), KazEOSat, tokens, private location details.
