# Licence and redistribution report (R40 archive)

Status: findings from the repository files and provenance notes; no legal review. Items marked DECISION need the author.

| Material | In archive? | Basis | Condition |
|---|---|---|---|
| Source code (research/R40_KZ, workflows) | yes | authored by the research project | **DECISION: the repository has no LICENSE file; manifest entries say "see repository", which points nowhere.** Choose a code licence (e.g. MIT or Apache-2.0) before publishing. |
| Result tables (CSV), figures, captions, reports | yes | authored output | **DECISION: record licence** (CC BY 4.0 proposed). |
| Copernicus GLO-30 derived rasters (elevation, slope, decision rasters) | yes (derived, 30 m UTM) | Copernicus DEM licence | attribution "Contains modified Copernicus data" (DLR/Airbus, EU/ESA) |
| NASADEM derived rasters | yes | NASA, public domain | citation requested |
| swissALTI3D (native-resolution analysis windows reference_native_*.tif and 30 m derived rasters) | yes | swisstopo OGD | attribution to swisstopo; check current OGD terms before publishing |
| USGS 3DEP (10 m analysis windows and derived rasters) | yes | public domain (USGS) | citation requested |
| OpenStreetMap boundaries, footprints, vector layers (boundaries/*.geojson, GPKG, derived footprints) | yes | ODbL 1.0 | attribution "© OpenStreetMap contributors"; **derived databases stay under ODbL (share-alike)**. A single CC BY label on the whole record would be inaccurate. |
| Natural Earth (overview maps) | yes (in figures) | public domain | none |
| ICESat-2 ATL08 v007 point samples (atl08_*.csv, GPKG) | yes (extracted segments) | NASA open data | citation of product |
| Sentinel-2 / Landsat / Sentinel-1 catalogues and derived NDVI/snow layers (r40-context, catalogs) | yes (catalogues, derived layers; not used in the manuscript results) | Copernicus / USGS open data | attribution |
| ALOS AW3D30 rasters | **no** | JAXA terms (registration/citation); not redistributed here | only derived statistics are included; reacquire via workflow (Planetary Computer) |
| FABDEM rasters | **no** | CC BY-NC-SA 4.0 | only derived statistics; ~45 % of FABDEM pixels in the OSM-centred Kok-Zhailau window are nodata |
| KazEOSat imagery | **no** (never obtained) | proprietary, no public catalogue | the repository contains only a data-request letter (KAZEOSAT_REQUEST_RU.md) and an empty probe result (kazeosat_probe.json = []) |
| Tokens, passwords, personal data | no | scan over all 18 refs and archive members found only the workflow guard regex lines | none |

Verification performed: no file name containing alos/fabdem/aw3d in any archive; the only kazeosat-named files are the request letter and the empty probe list; no occurrence of the author's street/home address in any ref or archive member (text search).

## Recommendation (author decides)
Split the deposit into (A) code, tables, figures, documentation under author-chosen licences (CC BY 4.0 for documents and tables, MIT/Apache-2.0 for code) and (B) OSM-derived vector data under ODbL 1.0, or deposit everything in one record with licence "other (open)" and this report as the licence statement. Zenodo's licence field takes one value, so the single-record route must point to LICENSES_REPORT.md.

## Companion file R35-R39
The source repository states in CODE_LICENSE_PROPOSAL_NOT_ACTIVE.md that the proposed licence (MIT or BSD-3-Clause) is not granted and that distribution rights of the legacy R34 source must be confirmed before public release. Do not deposit the companion file publicly until the author confirms.
