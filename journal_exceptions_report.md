# Exceptions report (journal edition)

Generated 2026-10-10T20:31:55+00:00. ERROR = product missing/failed or discrepancy; WARN = limitation; INFO = note.

## WARN (6)

- **data** - No lidar/DTM reference exists for Kazakhstan `Kazakhstan maps show transferred decisions; error is NOT measured there. ICESat-2 gives point samples along tracks only.`
- **data** - Distance-only decision rasters were never published `Figure B shows the combined rule (the rasters in r40-results). The distance-only shares exist only as table rows in decisions_by_site.csv.`
- **boundaries** - Official resort boundaries are not available `Medeu territory = a 0.043 km2 OSM sports-centre polygon (not the resort); Kok-Zhailau has no named OSM polygon; footprints are derived. None is an official border.`
- **data** - KazEOSat imagery not used `No public catalogue and no licence; proprietary pixels are not distributed.`
- **vertical datum** - Heights are not datum-harmonised in profile figures `EGM2008/EGM96/LN02/NAVD88 differ by metres; profile difference panels remove the median offset.`
- **common grid** - overlapping windows differ slightly in the overlap; first-valid pixel used. Likely cause (not tested): each window was warped separately from the geographic source grid, so sub-pixel coordinate approximation differs between windows; this is a property of the reused r40-results rasters, not of this package `{'cop_elevation_m': 'max 2.190, mean 0.287; 19.44% of 159338 overlap cells differ', 'nasadem_elevation_m': 'max 2.238, mean 0.265; 17.02% of 159338 overlap cells differ', 'cop_slope_deg': 'max 1.844, mean 0.098; 28.07% of 156524 overlap cells differ', 'nasadem_slope_deg': 'max 1.689, mean 0.093; 29.10% of 156524 overlap cells differ'}`

## INFO (3)

- **scope** - ALOS AW3D30 not mapped/packaged `not redistributed here (JAXA terms require citation/registration; raster use previously limited to statistics in the main run). Figures C use Copernicus GLO-30 and NASADEM only.`
- **scope** - FABDEM not mapped/packaged `CC BY-NC-SA 4.0 (non-commercial, share-alike) - raster not redistributed; the main run used it for statistics only. In the OSM-centred Kok-Zhailau window ~45 % of FABDEM pixels are nodata.`
- **ATL08** - documented strict-filter counts vs recomputed `docs: 1,484 strict segments / 897-902 pairs (see repository notes); recomputed Kazakhstan strict=1484, pairs_both_strict=902; sum over all five areas strict=3020`
