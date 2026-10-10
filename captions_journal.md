# R40 journal figures: captions

Each figure has a SHORT caption (paste into the manuscript) and TECHNICAL notes (methods/supplement). Figures are 180 mm wide, all text >= 7 pt, 300 dpi PNG + PDF + SVG.

## R40_Fig_A_study_area

**Caption.** Study area. (a) Location of the Kazakhstan study sites (KZ) and of the Swiss (CH) and US lidar validation regions. (b) Central Asia with the enlarged window. (c) Medeu, Shymbulak and two alternative Kok-Zhailau study windows (V1, V2) on Copernicus GLO-30 relief, 76.85-77.20 deg E, 43.05-43.25 deg N, UTM zone 43N. Coloured rectangles are analysis windows, not administrative borders. Solid lines are OpenStreetMap polygons and dashed lines are footprints derived from mapped objects; neither is an official boundary.

**Technical notes.** Map (c): Copernicus GLO-30 DSM (ESA/Copernicus; EGM2008; item dates 2021-04-22) reprojected bilinearly to the 30 m UTM grid; window frame = bounding box of the 76.85-77.20E, 43.05-43.25N quadrilateral in EPSG:32643 (the quadrilateral is rotated by the grid convergence, so the frame is slightly larger). Relief: Copernicus GLO-30 DSM, bicubic-resampled 2x for display only (cell 15 m), multi-directional hillshade (azimuths 225, 270, 315, 360 deg, altitude 40 deg, weights 0.15, 0.25, 0.35, 0.25), hypsometric tint (colour bar); analysis values stay on the packaged 30 m grid. Scale bar: exact metres in EPSG:32643; graticule from pyproj; north arrow rotated by the meridian convergence (values in tables/map_furniture_parameters.csv). Panel (a): Natural Earth 1:110m admin-0 countries, Robinson projection; panel (b): Natural Earth 1:50m, Lambert azimuthal equal-area (lat0 45N, lon0 70E); no scale bars because scale varies across these maps. Medeu: the only OSM polygon is a 0.043 km2 sports-centre polygon (not the resort); Shymbulak: OSM winter-sports polygon; footprints are derived (buffer 250 m, erosion 200 m of mapped aerialways/pistes/tourism/leisure features within 2.5-3.5 km of the configured centre). Kok-Zhailau V1 = configured centre (provisional, diamond); V2 = centre from OSM-named objects, about 5.9 km west. All outlines are exploratory. Overview raster: full-window Copernicus GLO-30 (inputs/rasters/overview_kz).

_Size: 180 x 197 mm._

## R40_Fig_A_suppl_validation_sites

**Caption.** Lidar validation sites. Davos-Parsenn and Zermatt-Gornergrat (Switzerland) and Alta-Snowbird and Park City (USA), each in its own UTM zone. Solid lines are OpenStreetMap polygons where one was found and dashed lines are footprints derived from mapped objects; neither is an official boundary.

**Technical notes.** Reference lidar DTMs: swissALTI3D 2 m (swisstopo OGD; LN02) and USGS 3DEP 1/3 arc-second (NAVD88). Relief: Copernicus GLO-30 DSM, bicubic-resampled 3x for display only (cell 10 m), multi-directional hillshade (azimuths 225, 270, 315, 360 deg, altitude 40 deg, weights 0.15, 0.25, 0.35, 0.25), grey scale; analysis values stay on the packaged 30 m grid. Scale bars: exact metres in each local UTM CRS; graticule from pyproj; north arrows rotated by the meridian convergence (tables/map_furniture_parameters.csv). Site centre = configured centre.

_Size: 180 x 202 mm._

## R40_Fig_B_decisions_15deg

**Caption.** Threshold decisions at 15 deg slope for the four Kazakhstan study windows (Medeu, Shymbulak, Kok-Zhailau V1 and V2). Colours show the classes of the combined abstention rule (BELOW, ABOVE, ABSTAIN); grey = no decision. The rule was trained on lidar-validated sites in Switzerland and the USA and is transferred here, so the error is not measured at these sites. Percentages are shares of valid 30 m pixels per window. Outlines are exploratory and not official boundaries.

**Technical notes.** Classes exactly as in decision_combined_t15_risk2.tif (codes 0 BELOW, 1 ABOVE, 2 ABSTAIN, 255 no decision; target training risk 0.02), 30 m cells, UTM 43N (EPSG:32643); class colours at 72 % opacity over the relief. Relief: Copernicus GLO-30 DSM, bicubic-resampled 3x for display only (cell 10 m), multi-directional hillshade (azimuths 225, 270, 315, 360 deg, altitude 40 deg, weights 0.15, 0.25, 0.35, 0.25), grey scale; analysis values stay on the packaged 30 m grid. Source DEM: Copernicus GLO-30 DSM (ESA/Copernicus; EGM2008; item dates 2021-04-22) reprojected bilinearly to the 30 m UTM grid. Outlines: solid = OSM-mapped named polygon (exploratory); dashed = footprint derived from mapped aerialways/pistes/tourism/leisure features (not an official boundary). Pixel-to-polygon masks: pixel centre inside the polygon (rasterio rasterize, all_touched=False). Per-mask counts, areas, shares and contour ids: tables/map_summary_figB.csv; check against decisions_by_site.csv: tables/verification_figB_vs_decisions_by_site.csv (30 of 30 comparisons OK in the first edition; this edition re-derives them: tables/consistency_vs_source_package.csv). Shares printed in the panel titles are recomputed from the drawn arrays (tables/journal_figure_shares_as_drawn.csv). Scale bar: exact metres in EPSG:32643; north arrow rotated by the meridian convergence (tables/map_furniture_parameters.csv).

_Size: 180 x 215 mm._

## R40_Fig_B_suppl_decisions_7.5deg

**Caption.** Threshold decisions at 7.5 deg slope for the four Kazakhstan study windows (Medeu, Shymbulak, Kok-Zhailau V1 and V2). Colours show the classes of the combined abstention rule (BELOW, ABOVE, ABSTAIN); grey = no decision. The rule was trained on lidar-validated sites in Switzerland and the USA and is transferred here, so the error is not measured at these sites. Percentages are shares of valid 30 m pixels per window. Outlines are exploratory and not official boundaries.

**Technical notes.** Classes exactly as in decision_combined_t7.5_risk2.tif (codes 0 BELOW, 1 ABOVE, 2 ABSTAIN, 255 no decision; target training risk 0.02), 30 m cells, UTM 43N (EPSG:32643); class colours at 72 % opacity over the relief. Relief: Copernicus GLO-30 DSM, bicubic-resampled 3x for display only (cell 10 m), multi-directional hillshade (azimuths 225, 270, 315, 360 deg, altitude 40 deg, weights 0.15, 0.25, 0.35, 0.25), grey scale; analysis values stay on the packaged 30 m grid. Source DEM: Copernicus GLO-30 DSM (ESA/Copernicus; EGM2008; item dates 2021-04-22) reprojected bilinearly to the 30 m UTM grid. Outlines: solid = OSM-mapped named polygon (exploratory); dashed = footprint derived from mapped aerialways/pistes/tourism/leisure features (not an official boundary). Pixel-to-polygon masks: pixel centre inside the polygon (rasterio rasterize, all_touched=False). Per-mask counts, areas, shares and contour ids: tables/map_summary_figB.csv; check against decisions_by_site.csv: tables/verification_figB_vs_decisions_by_site.csv (30 of 30 comparisons OK in the first edition; this edition re-derives them: tables/consistency_vs_source_package.csv). Shares printed in the panel titles are recomputed from the drawn arrays (tables/journal_figure_shares_as_drawn.csv). Scale bar: exact metres in EPSG:32643; north arrow rotated by the meridian convergence (tables/map_furniture_parameters.csv).

_Size: 180 x 215 mm._

## R40_Fig_B_suppl_decisions_25deg

**Caption.** Threshold decisions at 25 deg slope for the four Kazakhstan study windows (Medeu, Shymbulak, Kok-Zhailau V1 and V2). Colours show the classes of the combined abstention rule (BELOW, ABOVE, ABSTAIN); grey = no decision. The rule was trained on lidar-validated sites in Switzerland and the USA and is transferred here, so the error is not measured at these sites. Percentages are shares of valid 30 m pixels per window. Outlines are exploratory and not official boundaries.

**Technical notes.** Classes exactly as in decision_combined_t25_risk2.tif (codes 0 BELOW, 1 ABOVE, 2 ABSTAIN, 255 no decision; target training risk 0.02), 30 m cells, UTM 43N (EPSG:32643); class colours at 72 % opacity over the relief. Relief: Copernicus GLO-30 DSM, bicubic-resampled 3x for display only (cell 10 m), multi-directional hillshade (azimuths 225, 270, 315, 360 deg, altitude 40 deg, weights 0.15, 0.25, 0.35, 0.25), grey scale; analysis values stay on the packaged 30 m grid. Source DEM: Copernicus GLO-30 DSM (ESA/Copernicus; EGM2008; item dates 2021-04-22) reprojected bilinearly to the 30 m UTM grid. Outlines: solid = OSM-mapped named polygon (exploratory); dashed = footprint derived from mapped aerialways/pistes/tourism/leisure features (not an official boundary). Pixel-to-polygon masks: pixel centre inside the polygon (rasterio rasterize, all_touched=False). Per-mask counts, areas, shares and contour ids: tables/map_summary_figB.csv; check against decisions_by_site.csv: tables/verification_figB_vs_decisions_by_site.csv (30 of 30 comparisons OK in the first edition; this edition re-derives them: tables/consistency_vs_source_package.csv). Shares printed in the panel titles are recomputed from the drawn arrays (tables/journal_figure_shares_as_drawn.csv). Scale bar: exact metres in EPSG:32643; north arrow rotated by the meridian convergence (tables/map_furniture_parameters.csv).

_Size: 180 x 215 mm._

## R40_Fig_C1_kazakhstan_inter_dem_slope_difference

**Caption.** Slope differences between two global DEMs (NASADEM minus Copernicus GLO-30) in the four Kazakhstan windows, on the common valid mask. The map shows disagreement between DEMs, not accuracy: no lidar reference exists for Kazakhstan. Dashed line = derived footprint (exploratory).

**Technical notes.** Both DEMs are DSMs resampled bilinearly to the same 30 m UTM 43N grid; slopes by the Horn (1981) 3x3 method; common valid mask = pixels with a complete 3x3 neighbourhood in both DEMs. ALOS AW3D30 and FABDEM are not mapped (licence/redistribution; see exceptions report). Statistics (common pixels, mean, SD, MAE, RMSE, 95th percentile, class disagreement at 7.5/15/25 deg): tables/inter_dem_slope_difference_summary.csv. Colour scale diverging, symmetric, saturating at ±10 deg. Grey = no data. Scale bar: exact metres in EPSG:32643.

_Size: 180 x 215 mm._

## R40_Fig_C2_switzerland_dem_vs_lidar_slope_difference

**Caption.** Slope differences at the lidar validation sites in Switzerland: global DEM minus lidar-DTM reference and NASADEM minus Copernicus GLO-30, on the common valid mask of each pair. The lidar DTM is block-averaged to the 30 m cell before the slope is computed (support-matched). MAE is the mean absolute difference.

**Technical notes.** Global DEMs are DSMs (canopy and buildings included); the reference is a bare-earth DTM; no co-registration was applied. Slopes by the Horn (1981) 3x3 method on the 30 m grid. Zermatt includes glaciers whose surface changed between the lidar epoch and the DSMs. Statistics: tables/inter_dem_slope_difference_summary.csv. Each panel in its own local UTM CRS with an exact metric scale bar; graticule labels on the left column and the bottom row only; dashed line = derived footprint (exploratory); grey = no data.

_Size: 180 x 145 mm._

## R40_Fig_C2_usa_dem_vs_lidar_slope_difference

**Caption.** Slope differences at the lidar validation sites in USA: global DEM minus lidar-DTM reference and NASADEM minus Copernicus GLO-30, on the common valid mask of each pair. The lidar DTM is block-averaged to the 30 m cell before the slope is computed (support-matched). MAE is the mean absolute difference.

**Technical notes.** Global DEMs are DSMs (canopy and buildings included); the reference is a bare-earth DTM; no co-registration was applied. Slopes by the Horn (1981) 3x3 method on the 30 m grid. Zermatt includes glaciers whose surface changed between the lidar epoch and the DSMs. Statistics: tables/inter_dem_slope_difference_summary.csv. Each panel in its own local UTM CRS with an exact metric scale bar; graticule labels on the left column and the bottom row only; dashed line = derived footprint (exploratory); grey = no data.

_Size: 180 x 146 mm._

## R40_Fig_D_profile_davos_parsenn

**Caption.** Measured terrain profiles at Davos-Parsenn: two 3 km grid-aligned transects through the site centre (W–E, S–N) from the lidar DTM at native resolution, the same DTM averaged to the 30 m cell (support-matched reference) and the two global DSMs. Lower panels show DEM minus 30 m reference after removing the median offset.

**Technical notes.** Reference: swissALTI3D (LN02, 2 m; swisstopo OGD); candidates Copernicus GLO-30 (EGM2008) and NASADEM (EGM96), 30 m, sampled bilinearly. Vertical datums are not harmonised (geoid offsets of metres); the lower panels remove the median offset along each transect. DSMs include canopy/buildings, the reference is bare earth; no co-registration. Transects: rule-based (3 km, grid-aligned, through the configured site centre; derived/vector/profile_lines.geojson), not selected for agreement. Reference epoch: swissALTI3D release year(s) 2023 (25 tiles); Copernicus item date 2021-04-22; NASADEM item date 2000-02-20. Profile values: tables/profile_samples.csv; statistics: tables/profile_summary.csv. Map: hillshade of the lidar DTM (native resolution for 2 m data, 3x bicubic display resampling for the 10 m 3DEP window), multi-directional, grey; scale bar exact metres in the local UTM CRS; north arrow rotated by the meridian convergence.

_Size: 180 x 146 mm._

## R40_Fig_D_profile_zermatt_gornergrat

**Caption.** Measured terrain profiles at Zermatt-Gornergrat: two 3 km grid-aligned transects through the site centre (W–E, S–N) from the lidar DTM at native resolution, the same DTM averaged to the 30 m cell (support-matched reference) and the two global DSMs. Lower panels show DEM minus 30 m reference after removing the median offset.

**Technical notes.** Reference: swissALTI3D (LN02, 2 m; swisstopo OGD); candidates Copernicus GLO-30 (EGM2008) and NASADEM (EGM96), 30 m, sampled bilinearly. Vertical datums are not harmonised (geoid offsets of metres); the lower panels remove the median offset along each transect. DSMs include canopy/buildings, the reference is bare earth; no co-registration. Transects: rule-based (3 km, grid-aligned, through the configured site centre; derived/vector/profile_lines.geojson), not selected for agreement. Reference epoch: swissALTI3D release year(s) 2024 (20 tiles); Copernicus item date 2021-04-22; NASADEM item date 2000-02-20. Profile values: tables/profile_samples.csv; statistics: tables/profile_summary.csv. Map: hillshade of the lidar DTM (native resolution for 2 m data, 3x bicubic display resampling for the 10 m 3DEP window), multi-directional, grey; scale bar exact metres in the local UTM CRS; north arrow rotated by the meridian convergence.

_Size: 180 x 146 mm._

## R40_Fig_D_profile_alta_snowbird

**Caption.** Measured terrain profiles at Alta-Snowbird: two 3 km grid-aligned transects through the site centre (W–E, S–N) from the lidar DTM at native resolution, the same DTM averaged to the 30 m cell (support-matched reference) and the two global DSMs. Lower panels show DEM minus 30 m reference after removing the median offset.

**Technical notes.** Reference: USGS 3DEP 1/3 arc-second (NAVD88, ~10 m); candidates Copernicus GLO-30 (EGM2008) and NASADEM (EGM96), 30 m, sampled bilinearly. Vertical datums are not harmonised (geoid offsets of metres); the lower panels remove the median offset along each transect. DSMs include canopy/buildings, the reference is bare earth; no co-registration. Transects: rule-based (3 km, grid-aligned, through the configured site centre; derived/vector/profile_lines.geojson), not selected for agreement. Reference epoch: 1 USGS 3DEP item(s); per-item dates in inputs/provenance/alta_snowbird_reference_native_provenance.json (3DEP seamless is a mosaic of lidar projects of different years); Copernicus item date 2021-04-22; NASADEM item date 2000-02-20. Profile values: tables/profile_samples.csv; statistics: tables/profile_summary.csv. Map: hillshade of the lidar DTM (native resolution for 2 m data, 3x bicubic display resampling for the 10 m 3DEP window), multi-directional, grey; scale bar exact metres in the local UTM CRS; north arrow rotated by the meridian convergence.

_Size: 180 x 146 mm._

## R40_Fig_D_profile_park_city

**Caption.** Measured terrain profiles at Park City: two 3 km grid-aligned transects through the site centre (W–E, S–N) from the lidar DTM at native resolution, the same DTM averaged to the 30 m cell (support-matched reference) and the two global DSMs. Lower panels show DEM minus 30 m reference after removing the median offset.

**Technical notes.** Reference: USGS 3DEP 1/3 arc-second (NAVD88, ~10 m); candidates Copernicus GLO-30 (EGM2008) and NASADEM (EGM96), 30 m, sampled bilinearly. Vertical datums are not harmonised (geoid offsets of metres); the lower panels remove the median offset along each transect. DSMs include canopy/buildings, the reference is bare earth; no co-registration. Transects: rule-based (3 km, grid-aligned, through the configured site centre; derived/vector/profile_lines.geojson), not selected for agreement. Reference epoch: 1 USGS 3DEP item(s); per-item dates in inputs/provenance/park_city_reference_native_provenance.json (3DEP seamless is a mosaic of lidar projects of different years); Copernicus item date 2021-04-22; NASADEM item date 2000-02-20. Profile values: tables/profile_samples.csv; statistics: tables/profile_summary.csv. Map: hillshade of the lidar DTM (native resolution for 2 m data, 3x bicubic display resampling for the 10 m 3DEP window), multi-directional, grey; scale bar exact metres in the local UTM CRS; north arrow rotated by the meridian convergence.

_Size: 180 x 146 mm._

## R40_Fig_E_atl08_track_samples

**Caption.** Real ICESat-2 ATL08 terrain segments (100 m along-track) over the Kazakhstan window and the four lidar validation sites. Strict (uncertainty < 5 m) and lenient (< 15 m) subsets are shown on top of the other segments. Segments exist only along ground tracks; they are a partial independent reference and must not be read as validation of any full slope map.

**Technical notes.** ATL08 v007; common filters fixed before inspecting DEM errors: terrain height valid, >= 30 terrain photons, ATM cloud flag <= 2; lenient = height uncertainty < 15 m; strict = < 5 m. The strict subset is 1-4 % of all segments in every area. Counts in panel titles refer to the displayed extent; full-bbox counts: tables/atl08_filter_counts.csv. Heights are ellipsoidal (no geoid correction). Background: full-window Copernicus GLO-30 hillshade, grey scale (display resampling as in Figure A for panel a; 3x for b-e). Panel (a): 76.85-77.20 deg E, 43.05-43.25 deg N (UTM 43N); (b)-(e): lidar validation windows, each in its own local UTM CRS. Vector layers with quality flags: derived/vector/atl08_segments_and_tracks.gpkg. Granule acquisition dates (from granule names): Kazakhstan 2018-11-02 to 2026-07-18 (82 dates); Davos-Parsenn 2018-10-20 to 2026-05-27 (42 dates); Zermatt-Gornergrat 2018-12-22 to 2026-06-14 (47 dates); Alta-Snowbird 2018-11-02 to 2026-07-19 (38 dates); Park City 2019-01-31 to 2026-07-19 (36 dates).

_Size: 180 x 146 mm._
