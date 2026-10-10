# R40_CARTOGRAPHY_SOURCE_PACKAGE

Reproducible scientific GIS figures and source layers for R40 "Support-aware terrain threshold decisions" (Kazakhstan: Medeu, Shymbulak, two Kok-Zhailau variants;
validation: Davos-Parsenn, Zermatt-Gornergrat (CH), Alta-Snowbird, Park City (US)).

Generated: 2026-10-10T19:03:33+00:00  |  code commit: 2e1a31ed0f239e9bf8ad50aa73a5da2a705a87fc  |  workflow run: 38078170104

Reused result branches (commit hashes): {"r40-results": "cd948ccd214f525bf45731cf71a1537937e0843b", "r40-icesat2": "db4c640cd71871eb2c4b34ef5c2b52efe3c112c1", "r40-extra": "37f10c5f9c9c3c30725e6a0a621ef7e5f258ed8c"}

## Contents
* `inputs/` - assets REUSED from earlier verified runs (branch r40-results, r40-icesat2; SHA-256 re-checked against the original run in `inputs/provenance/reuse_integrity_check.csv`), plus freshly fetched native lidar-DTM windows and Natural Earth layers.
* `derived/rasters/` - separate nodata masks (1 = nodata), pixel-to-polygon masks (`mask_*.tif`), the aligned Kazakhstan common 30 m grid (`common_grid_kz/`).
* `derived/vector/` - `r40_cartography_vectors.gpkg` and GeoJSON: study polygons (both Kok-Zhailau candidates; field `geometry_origin`), study centres, common-grid extent, profile lines, ATL08 segments/tracks with quality flags.
* `figures/` - FigA (location, + supplement), FigB (15 deg decisions; supplements 7.5 and 25 deg), FigC1/C2 (inter-DEM and DEM-vs-lidar slope differences), FigD (profiles, four sites), FigE (ATL08 samples); PNG 300 dpi, PDF, SVG; full captions in `figures/CAPTIONS.md`.
* `tables/` - per-map summaries, verification against `decisions_by_site.csv`, inter-DEM statistics, ATL08 filter counts, profile samples and statistics.
* `manifest.csv` - every file with source, resolution, CRS, vertical datum, extent, acquisition dates, licence, SHA-256, generation commit and run id.
* `exceptions_report.md/.csv` - everything missing, flagged or deliberately excluded.
* `scripts/` - code + `rebuild_all.sh` (offline rebuild of all derived products from `inputs/`).

## Rules followed
* No generative AI for geography or raster values; no simulated landscape; missing data are marked, not replaced.
* Boundaries are OSM-mapped features or footprints derived from mapped objects and are labelled exploratory; NO official resort border is claimed.
* Maps use true coordinate transforms: local metric UTM CRS; scale bars are exact lengths in that CRS; graticules from pyproj; north arrows account for grid convergence.
* Figure B shows exactly the classes in the packaged `decision_combined_t*_risk2.tif`; its summaries were checked against `tables/decisions_by_site.csv` (tolerance 0.05 percentage points, identical pixel counts): 30 of 30 comparisons OK, 0 flagged. Flagged items are listed in the exceptions report and are NOT adjusted.
* Not included: KazEOSat pixels (no licence), tokens, private imagery, ALOS AW3D30 and FABDEM rasters (licence/redistribution), the user's private location details.

## Exact sources
* Copernicus GLO-30 and NASADEM: Microsoft Planetary Computer STAC API https://planetarycomputer.microsoft.com/api/stac/v1 (collections `cop-dem-glo-30`, `nasadem`; item ids and dates in `inputs/provenance/*_sources_provenance.json`, retrieved by run r40-results 38058021115).
* Lidar DTMs: swisstopo STAC https://data.geo.admin.ch/api/stac/v0.9 (collection ch.swisstopo.swissalti3d, 2 m); USGS 3DEP via Planetary Computer (`3dep-seamless`, 10 m).
* OSM polygons: Overpass API (endpoint, query and time in `inputs/boundaries/*_boundary_provenance.json`).
* ICESat-2 ATL08 v007: NASA NSIDC DAAC (segments extracted in branch r40-icesat2).
* Natural Earth admin-0 countries: naciscdn.org/naturalearth (1:110m, 1:50m).

## Licences / attribution
Copernicus GLO-30 (ESA/Copernicus, "Contains modified Copernicus data"); NASADEM (NASA/USGS, public domain); OpenStreetMap contributors (ODbL); Natural Earth (public domain);
swissALTI3D (swisstopo OGD); USGS 3DEP (public domain); NASA ICESat-2 ATL08 v007 (NSIDC DAAC).

## Rebuild
`bash scripts/rebuild_all.sh` (Python >= 3.10; numpy, scipy, rasterio, pyproj, shapely, geopandas, pyogrio, matplotlib). Network is not needed.
