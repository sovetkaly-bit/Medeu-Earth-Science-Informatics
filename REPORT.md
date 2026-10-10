# R40 — отчёт запуска (числа считаны из tables/*.csv)

## 1. Какие данные реально получены
| site | source | status |
|---|---|---|
| all | KazEOSat-1/2 | MANUAL_LICENSE_REQUIRED |
| all | planetary-computer | CATALOG_OK |
| alta_snowbird | 3dep-seamless | REFERENCE_READY |
| alta_snowbird | alos-dem | RASTER_READY |
| alta_snowbird | boundary | OSM_POLYGON_NAMED_MATCH |
| alta_snowbird | cop-dem-glo-30 | RASTER_READY |
| alta_snowbird | nasadem | RASTER_READY |
| davos_parsenn | alos-dem | RASTER_READY |
| davos_parsenn | boundary | OSM_POLYGON_NAMED_MATCH |
| davos_parsenn | cop-dem-glo-30 | RASTER_READY |
| davos_parsenn | nasadem | RASTER_READY |
| davos_parsenn | swissALTI3D | REFERENCE_READY |
| kok_zhailau | CDSE-S2 | FOUND |
| kok_zhailau | FABDEM | RASTER_READY |
| kok_zhailau | alos-dem | RASTER_READY |
| kok_zhailau | boundary | FUNCTIONAL_FOOTPRINT_ONLY |
| kok_zhailau | cop-dem-glo-30 | RASTER_READY |
| kok_zhailau | landsat-c2-l2 | NDVI_READY |
| kok_zhailau | nasadem | RASTER_READY |
| kok_zhailau | sentinel-1-grd | FOUND |
| kok_zhailau | sentinel-1-rtc | FOUND |
| kok_zhailau | sentinel-2-l2a | NDVI_READY |
| kok_zhailau_osm | CDSE-S2 | FOUND |
| kok_zhailau_osm | FABDEM | RASTER_READY |
| kok_zhailau_osm | alos-dem | RASTER_READY |
| kok_zhailau_osm | boundary | FUNCTIONAL_FOOTPRINT_ONLY |
| kok_zhailau_osm | cop-dem-glo-30 | RASTER_READY |
| kok_zhailau_osm | landsat-c2-l2 | NDVI_READY |
| kok_zhailau_osm | nasadem | RASTER_READY |
| kok_zhailau_osm | sentinel-1-grd | FOUND |
| kok_zhailau_osm | sentinel-1-rtc | FOUND |
| kok_zhailau_osm | sentinel-2-l2a | NDVI_READY |
| medeu | CDSE-S2 | FOUND |
| medeu | FABDEM | RASTER_READY |
| medeu | alos-dem | RASTER_READY |
| medeu | boundary | OSM_POLYGON_NAMED_MATCH |
| medeu | cop-dem-glo-30 | RASTER_READY |
| medeu | landsat-c2-l2 | NDVI_READY |
| medeu | nasadem | RASTER_READY |
| medeu | sentinel-1-grd | FOUND |
| medeu | sentinel-1-rtc | FOUND |
| medeu | sentinel-2-l2a | NDVI_READY |
| park_city | 3dep-seamless | REFERENCE_READY |
| park_city | alos-dem | RASTER_READY |
| park_city | boundary | OSM_POLYGON_NAMED_MATCH |
| park_city | cop-dem-glo-30 | RASTER_READY |
| park_city | nasadem | RASTER_READY |
| shymbulak | CDSE-S2 | FOUND |
| shymbulak | FABDEM | RASTER_READY |
| shymbulak | alos-dem | RASTER_READY |
| shymbulak | boundary | OSM_POLYGON_NAMED_MATCH |
| shymbulak | cop-dem-glo-30 | RASTER_READY |
| shymbulak | landsat-c2-l2 | NDVI_READY |
| shymbulak | nasadem | RASTER_READY |
| shymbulak | sentinel-1-grd | FOUND |
| shymbulak | sentinel-1-rtc | FOUND |
| shymbulak | sentinel-2-l2a | NDVI_READY |
| validation | R40-experiment | VALIDATION_DONE |
| zermatt_gornergrat | alos-dem | RASTER_READY |
| zermatt_gornergrat | boundary | OSM_POLYGON_NAMED_MATCH |
| zermatt_gornergrat | cop-dem-glo-30 | RASTER_READY |
| zermatt_gornergrat | nasadem | RASTER_READY |
| zermatt_gornergrat | swissALTI3D | REFERENCE_READY |

## 2. Границы территорий
| site | boundary_status | reference_dtm | dems |
|---|---|---|---|
| medeu | OSM_POLYGON_NAMED_MATCH | False | alos-dem, cop-dem-glo-30, fabdem, nasadem |
| shymbulak | OSM_POLYGON_NAMED_MATCH | False | alos-dem, cop-dem-glo-30, fabdem, nasadem |
| kok_zhailau | FUNCTIONAL_FOOTPRINT_ONLY | False | alos-dem, cop-dem-glo-30, fabdem, nasadem |
| kok_zhailau_osm | FUNCTIONAL_FOOTPRINT_ONLY | False | alos-dem, cop-dem-glo-30, fabdem, nasadem |
| davos_parsenn | OSM_POLYGON_NAMED_MATCH | True | alos-dem, cop-dem-glo-30, nasadem |
| zermatt_gornergrat | OSM_POLYGON_NAMED_MATCH | True | alos-dem, cop-dem-glo-30, nasadem |
| alta_snowbird | OSM_POLYGON_NAMED_MATCH | True | alos-dem, cop-dem-glo-30, nasadem |
| park_city | OSM_POLYGON_NAMED_MATCH | True | alos-dem, cop-dem-glo-30, nasadem |

## 3. Контроль DEM
| site | dem | valid_px | nodata_pct | min_m | max_m | vertical_datum | type |
|---|---|---|---|---|---|---|---|
| medeu | cop-dem-glo-30 | 1.231e+05 | 0 | 1074 | 3461 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| medeu | nasadem | 1.231e+05 | 0 | 1077 | 3441 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| medeu | alos-dem | 1.231e+05 | 0 | 1077 | 3472 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| medeu | fabdem | 1.003e+05 | 18.51 | 1152 | 3461 | EGM2008 | DEM with forest/building correction (still modelled, not LiDAR DTM) |
| shymbulak | cop-dem-glo-30 | 9.878e+04 | 0 | 1420 | 4275 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| shymbulak | nasadem | 9.878e+04 | 0 | 1421 | 4273 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| shymbulak | alos-dem | 9.878e+04 | 0 | 1422 | 4302 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| shymbulak | fabdem | 9.878e+04 | 0 | 1419 | 4275 | EGM2008 | DEM with forest/building correction (still modelled, not LiDAR DTM) |
| kok_zhailau | cop-dem-glo-30 | 7.74e+04 | 0 | 1828 | 4092 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| kok_zhailau | nasadem | 7.74e+04 | 0 | 1826 | 4110 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| kok_zhailau | alos-dem | 7.74e+04 | 0 | 1813 | 4150 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| kok_zhailau | fabdem | 7.74e+04 | 0 | 1825 | 4091 | EGM2008 | DEM with forest/building correction (still modelled, not LiDAR DTM) |
| kok_zhailau_osm | cop-dem-glo-30 | 7.29e+04 | 0 | 1240 | 3318 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| kok_zhailau_osm | nasadem | 7.29e+04 | 0 | 1239 | 3314 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| kok_zhailau_osm | alos-dem | 7.29e+04 | 0 | 1242 | 3321 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| kok_zhailau_osm | fabdem | 4e+04 | 45.13 | 1297 | 3318 | EGM2008 | DEM with forest/building correction (still modelled, not LiDAR DTM) |
| davos_parsenn | cop-dem-glo-30 | 9.364e+04 | 0 | 1299 | 2826 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| davos_parsenn | nasadem | 9.364e+04 | 0 | 1296 | 2825 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| davos_parsenn | alos-dem | 9.364e+04 | 0 | 1279 | 2827 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| zermatt_gornergrat | cop-dem-glo-30 | 9.547e+04 | 0 | 1588 | 3445 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| zermatt_gornergrat | nasadem | 9.547e+04 | 0 | 1592 | 3435 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| zermatt_gornergrat | alos-dem | 9.547e+04 | 0 | 1591 | 3459 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| alta_snowbird | cop-dem-glo-30 | 9.364e+04 | 0 | 2249 | 3492 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| alta_snowbird | nasadem | 9.364e+04 | 0 | 2250 | 3475 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| alta_snowbird | alos-dem | 9.364e+04 | 0 | 2248 | 3497 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| park_city | cop-dem-glo-30 | 9.364e+04 | 0 | 1962 | 3056 | EGM2008 orthometric | DSM (surface), not bare-earth DTM |
| park_city | nasadem | 9.364e+04 | 0 | 1962 | 3049 | EGM96 orthometric | DSM (surface), not bare-earth DTM |
| park_city | alos-dem | 9.364e+04 | 0 | 1965 | 3059 | EGM96 orthometric | DSM (surface), not bare-earth DTM |

## 4. Валидация (LOSO: обучение на других территориях, оценка на удержанной)
AURC — площадь под кривой risk–coverage (меньше = лучше). random = доля ошибок без отказов.

### Порог 7.5°
| method | n_pixels | AURC | AURC_95CI | dAURC_vs_distance_95CI | E_AURC | risk@0.90 | risk@0.70 |
|---|---|---|---|---|---|---|---|
| random | 3.618e+05 | 0.03026 | [0.0256; 0.0362] | [+0.0237; +0.0329] | 0.0298 | 0.0302 | 0.03026 |
| distance | 3.618e+05 | 0.002593 | [0.0019; 0.0034] | [+0.0000; +0.0000] | 0.002131 | 0.009717 | 0.0007858 |
| norm_margin | 3.618e+05 | 0.002551 | [0.0019; 0.0034] | [-0.0002; +0.0002] | 0.002089 | 0.008086 | 0.001414 |
| dem_disagreement | 3.618e+05 | 0.0184 | [0.0149; 0.0223] | [+0.0129; +0.0191] | 0.01794 | 0.01548 | 0.01721 |
| dem_slope_spread | 3.618e+05 | 0.02796 | [0.0241; 0.0332] | [+0.0221; +0.0299] | 0.0275 | 0.02976 | 0.02903 |
| local_variability | 3.618e+05 | 0.03338 | [0.0254; 0.0424] | [+0.0234; +0.0391] | 0.03292 | 0.03004 | 0.0311 |
| scale_stability | 3.618e+05 | 0.03373 | [0.0263; 0.0408] | [+0.0240; +0.0373] | 0.03327 | 0.03125 | 0.0328 |
| combined | 3.618e+05 | 0.00269 | [0.0018; 0.0037] | [-0.0001; +0.0003] | 0.002229 | 0.009631 | 0.001129 |

### Порог 15°
| method | n_pixels | AURC | AURC_95CI | dAURC_vs_distance_95CI | E_AURC | risk@0.90 | risk@0.70 |
|---|---|---|---|---|---|---|---|
| random | 3.618e+05 | 0.04918 | [0.0469; 0.0563] | [+0.0393; +0.0459] | 0.04795 | 0.04905 | 0.04919 |
| distance | 3.618e+05 | 0.008298 | [0.0071; 0.0105] | [+0.0000; +0.0000] | 0.007066 | 0.02375 | 0.009615 |
| norm_margin | 3.618e+05 | 0.007681 | [0.0067; 0.0098] | [-0.0011; -0.0000] | 0.006448 | 0.02254 | 0.007107 |
| dem_disagreement | 3.618e+05 | 0.02793 | [0.0263; 0.0322] | [+0.0183; +0.0227] | 0.0267 | 0.02685 | 0.02686 |
| dem_slope_spread | 3.618e+05 | 0.04002 | [0.0382; 0.0459] | [+0.0304; +0.0365] | 0.03879 | 0.04694 | 0.04347 |
| local_variability | 3.618e+05 | 0.03495 | [0.0319; 0.0408] | [+0.0242; +0.0302] | 0.03372 | 0.04581 | 0.04054 |
| scale_stability | 3.618e+05 | 0.04322 | [0.0402; 0.0503] | [+0.0322; +0.0395] | 0.04199 | 0.04987 | 0.04738 |
| combined | 3.618e+05 | 0.007747 | [0.0064; 0.0101] | [-0.0011; -0.0002] | 0.006515 | 0.02186 | 0.007281 |

### Порог 25°
| method | n_pixels | AURC | AURC_95CI | dAURC_vs_distance_95CI | E_AURC | risk@0.90 | risk@0.70 |
|---|---|---|---|---|---|---|---|
| random | 3.618e+05 | 0.0562 | [0.0516; 0.0601] | [+0.0409; +0.0472] | 0.05455 | 0.05677 | 0.05656 |
| distance | 3.618e+05 | 0.01141 | [0.0101; 0.0146] | [+0.0000; +0.0000] | 0.009757 | 0.02906 | 0.01157 |
| norm_margin | 3.618e+05 | 0.009133 | [0.0078; 0.0111] | [-0.0036; -0.0016] | 0.007482 | 0.02775 | 0.008541 |
| dem_disagreement | 3.618e+05 | 0.02547 | [0.0236; 0.0295] | [+0.0122; +0.0175] | 0.02382 | 0.03476 | 0.02454 |
| dem_slope_spread | 3.618e+05 | 0.03726 | [0.0346; 0.0424] | [+0.0236; +0.0301] | 0.03561 | 0.05012 | 0.04243 |
| local_variability | 3.618e+05 | 0.03618 | [0.0324; 0.0409] | [+0.0212; +0.0285] | 0.03453 | 0.05063 | 0.04453 |
| scale_stability | 3.618e+05 | 0.04176 | [0.0376; 0.0478] | [+0.0269; +0.0351] | 0.04011 | 0.0536 | 0.04774 |
| combined | 3.618e+05 | 0.009577 | [0.0077; 0.0126] | [-0.0028; -0.0013] | 0.007927 | 0.02581 | 0.007858 |

### Калибровка комбинированной модели (LOSO)
| ECE | Brier | Brier_const | Brier_skill | threshold_deg | n |
|---|---|---|---|---|---|
| 0.004732 | 0.02432 | 0.02932 | 0.1707 | 7.5 | 3.618e+05 |
| 0.003169 | 0.03853 | 0.04681 | 0.177 | 15 | 3.618e+05 |
| 0.002576 | 0.0427 | 0.05367 | 0.2043 | 25 | 3.618e+05 |

### Рабочие точки: порог неопределённости зафиксирован на обучающих территориях, оценка на удержанной
| threshold_deg | heldout_site | method | target_risk_train | coverage_heldout | selective_risk_heldout | full_coverage_error_heldout |
|---|---|---|---|---|---|---|
| 7.5 | davos_parsenn | combined | 0.01 | 0.9373 | 0.003058 | 0.0155 |
| 7.5 | davos_parsenn | distance | 0.01 | 0.9056 | 0.002417 | 0.0155 |
| 7.5 | zermatt_gornergrat | combined | 0.01 | 0.9542 | 0.03671 | 0.05222 |
| 7.5 | zermatt_gornergrat | distance | 0.01 | 0.943 | 0.03405 | 0.05222 |
| 7.5 | alta_snowbird | combined | 0.01 | 0.9523 | 0.0056 | 0.02001 |
| 7.5 | alta_snowbird | distance | 0.01 | 0.933 | 0.005026 | 0.02001 |
| 7.5 | park_city | combined | 0.01 | 0.9009 | 0.009707 | 0.03278 |
| 7.5 | park_city | distance | 0.01 | 0.8397 | 0.005955 | 0.03278 |
| 7.5 | davos_parsenn | combined | 0.02 | 0.9718 | 0.008209 | 0.0155 |
| 7.5 | davos_parsenn | distance | 0.02 | 0.9647 | 0.006427 | 0.0155 |
| 7.5 | zermatt_gornergrat | combined | 0.02 | 0.9932 | 0.04963 | 0.05222 |
| 7.5 | zermatt_gornergrat | distance | 0.02 | 0.9922 | 0.04898 | 0.05222 |
| 7.5 | alta_snowbird | combined | 0.02 | 0.9795 | 0.01185 | 0.02001 |
| 7.5 | alta_snowbird | distance | 0.02 | 0.9764 | 0.01129 | 0.02001 |
| 7.5 | park_city | combined | 0.02 | 0.9729 | 0.02243 | 0.03278 |
| 7.5 | park_city | distance | 0.02 | 0.9529 | 0.01805 | 0.03278 |
| 7.5 | davos_parsenn | combined | 0.03 | 0.9907 | 0.01246 | 0.0155 |
| 7.5 | davos_parsenn | distance | 0.03 | 0.991 | 0.01197 | 0.0155 |
| 7.5 | zermatt_gornergrat | combined | 0.03 | 1 | 0.05222 | 0.05222 |
| 7.5 | zermatt_gornergrat | distance | 0.03 | 1 | 0.05222 | 0.05222 |
| 7.5 | alta_snowbird | combined | 0.03 | 0.9943 | 0.01715 | 0.02001 |
| 7.5 | alta_snowbird | distance | 0.03 | 0.9953 | 0.01781 | 0.02001 |
| 7.5 | park_city | combined | 0.03 | 1 | 0.03278 | 0.03278 |
| 7.5 | park_city | distance | 0.03 | 1 | 0.03277 | 0.03278 |
| 15 | davos_parsenn | combined | 0.01 | 0.7765 | 0.003491 | 0.03219 |
| 15 | davos_parsenn | distance | 0.01 | 0.6532 | 0.002909 | 0.03219 |
| 15 | zermatt_gornergrat | combined | 0.01 | 0.8635 | 0.02669 | 0.05838 |
| 15 | zermatt_gornergrat | distance | 0.01 | 0.8358 | 0.02914 | 0.05838 |
| 15 | alta_snowbird | combined | 0.01 | 0.8173 | 0.006675 | 0.04567 |
| 15 | alta_snowbird | distance | 0.01 | 0.7141 | 0.004279 | 0.04567 |
| 15 | park_city | combined | 0.01 | 0.7681 | 0.01079 | 0.06053 |
| 15 | park_city | distance | 0.01 | 0.5919 | 0.004411 | 0.06053 |
| 15 | davos_parsenn | combined | 0.02 | 0.8741 | 0.007589 | 0.03219 |
| 15 | davos_parsenn | distance | 0.02 | 0.8293 | 0.007744 | 0.03219 |
| 15 | zermatt_gornergrat | combined | 0.02 | 0.9244 | 0.03552 | 0.05838 |
| 15 | zermatt_gornergrat | distance | 0.02 | 0.9195 | 0.03751 | 0.05838 |
| 15 | alta_snowbird | combined | 0.02 | 0.9042 | 0.01713 | 0.04567 |
| 15 | alta_snowbird | distance | 0.02 | 0.8766 | 0.01524 | 0.04567 |
| 15 | park_city | combined | 0.02 | 0.8959 | 0.02753 | 0.06053 |
| 15 | park_city | distance | 0.02 | 0.8304 | 0.01964 | 0.06053 |
| 15 | davos_parsenn | combined | 0.03 | 0.9235 | 0.01258 | 0.03219 |
| 15 | davos_parsenn | distance | 0.03 | 0.9117 | 0.01283 | 0.03219 |
| 15 | zermatt_gornergrat | combined | 0.03 | 0.9596 | 0.0437 | 0.05838 |
| 15 | zermatt_gornergrat | distance | 0.03 | 0.9615 | 0.04562 | 0.05838 |
| 15 | alta_snowbird | combined | 0.03 | 0.9467 | 0.02699 | 0.04567 |
| 15 | alta_snowbird | distance | 0.03 | 0.9442 | 0.02676 | 0.04567 |
| 15 | park_city | combined | 0.03 | 0.9544 | 0.0434 | 0.06053 |
| 15 | park_city | distance | 0.03 | 0.9306 | 0.03744 | 0.06053 |
| 25 | davos_parsenn | combined | 0.01 | 0.7101 | 0.004725 | 0.04954 |
| 25 | davos_parsenn | distance | 0.01 | 0.5669 | 0.003293 | 0.04954 |
| 25 | zermatt_gornergrat | combined | 0.01 | 0.8209 | 0.02261 | 0.06849 |
| 25 | zermatt_gornergrat | distance | 0.01 | 0.7873 | 0.02926 | 0.06849 |
| 25 | alta_snowbird | combined | 0.01 | 0.7585 | 0.009492 | 0.05741 |
| 25 | alta_snowbird | distance | 0.01 | 0.622 | 0.006502 | 0.05741 |
| 25 | park_city | combined | 0.01 | 0.788 | 0.007149 | 0.05194 |
| 25 | park_city | distance | 0.01 | 0.6328 | 0.001844 | 0.05194 |
| 25 | davos_parsenn | combined | 0.02 | 0.8344 | 0.01136 | 0.04954 |
| 25 | davos_parsenn | distance | 0.02 | 0.7709 | 0.01137 | 0.04954 |
| 25 | zermatt_gornergrat | combined | 0.02 | 0.898 | 0.03399 | 0.06849 |
| 25 | zermatt_gornergrat | distance | 0.02 | 0.8871 | 0.03944 | 0.06849 |
| 25 | alta_snowbird | combined | 0.02 | 0.8666 | 0.0199 | 0.05741 |
| 25 | alta_snowbird | distance | 0.02 | 0.8154 | 0.01789 | 0.05741 |
| 25 | park_city | combined | 0.02 | 0.8937 | 0.01861 | 0.05194 |
| 25 | park_city | distance | 0.02 | 0.814 | 0.01099 | 0.05194 |
| 25 | davos_parsenn | combined | 0.03 | 0.899 | 0.02027 | 0.04954 |
| 25 | davos_parsenn | distance | 0.03 | 0.8699 | 0.01926 | 0.04954 |
| 25 | zermatt_gornergrat | combined | 0.03 | 0.9425 | 0.04609 | 0.06849 |
| 25 | zermatt_gornergrat | distance | 0.03 | 0.9393 | 0.04922 | 0.06849 |
| 25 | alta_snowbird | combined | 0.03 | 0.9162 | 0.02963 | 0.05741 |
| 25 | alta_snowbird | distance | 0.03 | 0.9051 | 0.02955 | 0.05741 |
| 25 | park_city | combined | 0.03 | 0.9383 | 0.02921 | 0.05194 |
| 25 | park_city | distance | 0.03 | 0.8997 | 0.02176 | 0.05194 |

### Стресс-тесты (AURC, pooled LOSO)
| threshold_deg | stress | n_pixels | error_rate_full_coverage | AURC_random | AURC_distance | AURC_norm_margin | AURC_dem_disagreement | AURC_dem_slope_spread | AURC_local_variability | AURC_scale_stability | AURC_combined |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 7.5 | baseline | 3.618e+05 | 0.03024 | 0.02977 | 0.002593 | 0.002551 | 0.0184 | 0.02796 | 0.03338 | 0.03373 | 0.002652 |
| 7.5 | noise_2m | 3.618e+05 | 0.03789 | 0.03771 | 0.0032 | 0.003353 | 0.01971 | 0.03545 | 0.04373 | 0.04341 | 0.003125 |
| 7.5 | noise_5m | 3.618e+05 | 0.062 | 0.06149 | 0.006722 | 0.007107 | 0.02559 | 0.05356 | 0.07266 | 0.0646 | 0.005374 |
| 7.5 | support_60m | 8.688e+04 | 0.02051 | 0.02082 | 0.001418 | 0.00123 | 0.01179 | 0.01643 | 0.02513 | 0.02623 | 0.001639 |
| 7.5 | support_90m | 3.686e+04 | 0.01614 | 0.01571 | 0.001049 | 0.0008218 | 0.008718 | 0.01172 | 0.01773 | 0.0202 | 0.001297 |
| 7.5 | algorithm_zt | 3.618e+05 | 0.03384 | 0.03352 | 0.003049 | 0.003051 | 0.02077 | 0.03213 | 0.03734 | 0.0366 | 0.003052 |
| 7.5 | algorithm_evans | 3.618e+05 | 0.02992 | 0.02916 | 0.002528 | 0.002489 | 0.01806 | 0.02751 | 0.03322 | 0.03364 | 0.002607 |
| 7.5 | reference_fraction_rule_B | 3.618e+05 | 0.05136 | 0.05103 | 0.005208 | 0.006509 | 0.04222 | 0.05449 | 0.05928 | 0.06018 | 0.004903 |
| 7.5 | primary_nasadem | 3.618e+05 | 0.05006 | 0.04951 | 0.005181 | 0.004491 | 0.01893 | 0.03888 | 0.05957 | 0.05728 | 0.003666 |
| 7.5 | primary_alos | 3.618e+05 | 0.03688 | 0.03598 | 0.003414 | 0.003044 | 0.01863 | 0.03357 | 0.03688 | 0.03858 | 0.002728 |
| 15 | baseline | 3.618e+05 | 0.04924 | 0.04902 | 0.008298 | 0.007681 | 0.02793 | 0.04002 | 0.03495 | 0.04322 | 0.007607 |
| 15 | noise_2m | 3.618e+05 | 0.05888 | 0.0579 | 0.009454 | 0.009399 | 0.03118 | 0.05101 | 0.04509 | 0.05507 | 0.008679 |
| 15 | noise_5m | 3.618e+05 | 0.08823 | 0.08685 | 0.01582 | 0.01651 | 0.03978 | 0.07076 | 0.0749 | 0.08593 | 0.01312 |
| 15 | support_60m | 8.688e+04 | 0.03322 | 0.03304 | 0.00478 | 0.003682 | 0.01754 | 0.02451 | 0.02283 | 0.03252 | 0.004847 |
| 15 | support_90m | 3.686e+04 | 0.02574 | 0.02611 | 0.004023 | 0.002659 | 0.01166 | 0.01647 | 0.01884 | 0.02595 | 0.003996 |
| 15 | algorithm_zt | 3.618e+05 | 0.05576 | 0.05528 | 0.009879 | 0.009407 | 0.03278 | 0.04641 | 0.03986 | 0.04731 | 0.009078 |
| 15 | algorithm_evans | 3.618e+05 | 0.04808 | 0.04797 | 0.00797 | 0.007304 | 0.02698 | 0.03862 | 0.03422 | 0.04239 | 0.007255 |
| 15 | reference_fraction_rule_B | 3.618e+05 | 0.09795 | 0.09793 | 0.02298 | 0.02717 | 0.07845 | 0.09247 | 0.07803 | 0.09477 | 0.02039 |
| 15 | primary_nasadem | 3.618e+05 | 0.09185 | 0.09111 | 0.01904 | 0.01481 | 0.02996 | 0.05846 | 0.0786 | 0.0903 | 0.01156 |
| 15 | primary_alos | 3.618e+05 | 0.06043 | 0.0601 | 0.009777 | 0.008991 | 0.02868 | 0.04836 | 0.04242 | 0.05378 | 0.007824 |
| 25 | baseline | 3.618e+05 | 0.0569 | 0.05753 | 0.01141 | 0.009133 | 0.02547 | 0.03726 | 0.03618 | 0.04176 | 0.00953 |
| 25 | noise_2m | 3.618e+05 | 0.0646 | 0.06523 | 0.01249 | 0.01087 | 0.03015 | 0.0482 | 0.04474 | 0.05081 | 0.01084 |
| 25 | noise_5m | 3.618e+05 | 0.08936 | 0.09032 | 0.01825 | 0.01786 | 0.04026 | 0.07136 | 0.07243 | 0.07693 | 0.01568 |
| 25 | support_60m | 8.688e+04 | 0.03266 | 0.0336 | 0.005102 | 0.003259 | 0.01402 | 0.02023 | 0.02133 | 0.02305 | 0.00405 |
| 25 | support_90m | 3.686e+04 | 0.02485 | 0.02499 | 0.002884 | 0.001511 | 0.01039 | 0.01492 | 0.01611 | 0.01581 | 0.00231 |
| 25 | algorithm_zt | 3.618e+05 | 0.06444 | 0.06442 | 0.0137 | 0.01137 | 0.03031 | 0.0436 | 0.04055 | 0.04799 | 0.01145 |
| 25 | algorithm_evans | 3.618e+05 | 0.05535 | 0.05602 | 0.01095 | 0.008763 | 0.0248 | 0.0363 | 0.03535 | 0.04067 | 0.009233 |
| 25 | reference_fraction_rule_B | 3.618e+05 | 0.1197 | 0.1196 | 0.0403 | 0.03829 | 0.07881 | 0.09005 | 0.07851 | 0.09497 | 0.03199 |
| 25 | primary_nasadem | 3.618e+05 | 0.1086 | 0.1096 | 0.02917 | 0.01809 | 0.02833 | 0.0544 | 0.07448 | 0.08454 | 0.01499 |
| 25 | primary_alos | 3.618e+05 | 0.06194 | 0.0626 | 0.01149 | 0.00968 | 0.02604 | 0.04224 | 0.03996 | 0.04748 | 0.009364 |

### Ошибка глобальных DEM относительно независимой эталонной DTM
| site | dem | n_elev | elev_bias_m_incl_datum | elev_median_m | elev_rmse_debiased_m | elev_NMAD_m | slope_bias_deg | slope_rmse_deg | slope_MAE_deg | n_slope |
|---|---|---|---|---|---|---|---|---|---|---|
| davos_parsenn | cop-dem-glo-30 | 9.364e+04 | 1.603 | 0.2351 | 5.255 | 1.825 | -0.243 | 2.273 | 1.335 | 9.242e+04 |
| davos_parsenn | nasadem | 9.364e+04 | 3.198 | 2.841 | 7.27 | 5.316 | -0.9955 | 4.184 | 3.066 | 9.242e+04 |
| davos_parsenn | alos-dem | 9.364e+04 | 0.7566 | 0.4349 | 5.243 | 3.902 | -0.2709 | 2.673 | 1.86 | 9.242e+04 |
| zermatt_gornergrat | cop-dem-glo-30 | 9.547e+04 | 6.839 | 1.243 | 17.73 | 3.767 | -1.002 | 4.513 | 2.598 | 9.424e+04 |
| zermatt_gornergrat | nasadem | 9.547e+04 | 12.4 | 3.128 | 28.65 | 8.894 | -1.975 | 6.152 | 4.202 | 9.424e+04 |
| zermatt_gornergrat | alos-dem | 9.547e+04 | 11.78 | 4.755 | 19.13 | 4.899 | -0.6993 | 3.801 | 2.216 | 9.424e+04 |
| alta_snowbird | cop-dem-glo-30 | 9.364e+04 | 0.1966 | 0.1494 | 6.936 | 3.506 | -0.407 | 3.053 | 1.956 | 9.242e+04 |
| alta_snowbird | nasadem | 9.364e+04 | 1.259 | 1.856 | 8.808 | 6.925 | -1.363 | 4.92 | 3.542 | 9.242e+04 |
| alta_snowbird | alos-dem | 9.364e+04 | 2.035 | 2.131 | 6.652 | 4.975 | -0.138 | 2.81 | 1.91 | 9.242e+04 |
| park_city | cop-dem-glo-30 | 9.364e+04 | 1.826 | 0.4937 | 4.072 | 2.352 | -0.1885 | 2.195 | 1.446 | 9.242e+04 |
| park_city | nasadem | 9.364e+04 | 2.934 | 1.858 | 5.306 | 4.167 | -0.8809 | 2.99 | 2.175 | 9.242e+04 |
| park_city | alos-dem | 9.364e+04 | 4.707 | 3.519 | 5.067 | 3.701 | -0.08612 | 2.598 | 1.786 | 9.242e+04 |

### Согласие DEM как «подтверждение»?
| site | threshold_deg | n | unanimous_share | error_rate_when_unanimous | error_rate_when_split | share_of_any_dem_errors_that_are_shared_by_all | error_rate_cop-dem-glo-30 | error_rate_nasadem | error_rate_alos-dem |
|---|---|---|---|---|---|---|---|---|---|
| davos_parsenn | 7.5 | 9.242e+04 | 0.9557 | 0.00762 | 0.1924 | 0.1413 | 0.0158 | 0.03588 | 0.02788 |
| zermatt_gornergrat | 7.5 | 9.424e+04 | 0.9217 | 0.02846 | 0.3211 | 0.251 | 0.05136 | 0.08041 | 0.05305 |
| alta_snowbird | 7.5 | 9.242e+04 | 0.9651 | 0.00953 | 0.3225 | 0.2087 | 0.02044 | 0.03182 | 0.02061 |
| park_city | 7.5 | 9.242e+04 | 0.933 | 0.01495 | 0.2826 | 0.1724 | 0.03287 | 0.05094 | 0.0454 |
| davos_parsenn | 15 | 9.242e+04 | 0.8975 | 0.01613 | 0.1792 | 0.1238 | 0.03284 | 0.08502 | 0.05565 |
| zermatt_gornergrat | 15 | 9.424e+04 | 0.8939 | 0.03558 | 0.2485 | 0.2307 | 0.05816 | 0.1109 | 0.06262 |
| alta_snowbird | 15 | 9.242e+04 | 0.9138 | 0.02224 | 0.2964 | 0.1907 | 0.04588 | 0.07825 | 0.04751 |
| park_city | 15 | 9.242e+04 | 0.8908 | 0.03203 | 0.2952 | 0.2071 | 0.06077 | 0.09278 | 0.07594 |
| davos_parsenn | 25 | 9.242e+04 | 0.8583 | 0.02374 | 0.2098 | 0.1257 | 0.0501 | 0.1212 | 0.06865 |
| zermatt_gornergrat | 25 | 9.424e+04 | 0.8769 | 0.03438 | 0.3118 | 0.1967 | 0.06853 | 0.1184 | 0.06111 |
| alta_snowbird | 25 | 9.242e+04 | 0.8731 | 0.02854 | 0.2559 | 0.1641 | 0.05739 | 0.1174 | 0.05897 |
| park_city | 25 | 9.242e+04 | 0.9127 | 0.02603 | 0.3184 | 0.214 | 0.05155 | 0.07627 | 0.05825 |

## 5. Казахстан: решения (ошибка не измерена, модель перенесена)
| site | mask | threshold_deg | method | n_px | BELOW_pct | ABOVE_pct | ABSTAIN_pct |
|---|---|---|---|---|---|---|---|
| medeu | context | 7.5 | combined | 1.189e+05 | 2.737 | 95.78 | 1.487 |
| medeu | context | 7.5 | distance_only | 1.189e+05 | 3.218 | 95.44 | 1.343 |
| medeu | territory_osm_polygon | 7.5 | combined | 49 | 34.69 | 55.1 | 10.2 |
| medeu | territory_osm_polygon | 7.5 | distance_only | 49 | 34.69 | 48.98 | 16.33 |
| medeu | functional_footprint_derived | 7.5 | combined | 1.066e+04 | 9.545 | 86.16 | 4.294 |
| medeu | functional_footprint_derived | 7.5 | distance_only | 1.066e+04 | 11.24 | 85.38 | 3.376 |
| medeu | context | 15 | combined | 1.189e+05 | 9.261 | 82.74 | 7.996 |
| medeu | context | 15 | distance_only | 1.189e+05 | 9.936 | 81.52 | 8.541 |
| medeu | territory_osm_polygon | 15 | combined | 49 | 73.47 | 16.33 | 10.2 |
| medeu | territory_osm_polygon | 15 | distance_only | 49 | 73.47 | 16.33 | 10.2 |
| medeu | functional_footprint_derived | 15 | combined | 1.066e+04 | 24.62 | 61.18 | 14.2 |
| medeu | functional_footprint_derived | 15 | distance_only | 1.066e+04 | 25.87 | 59.72 | 14.41 |
| medeu | context | 25 | combined | 1.189e+05 | 31.73 | 52.85 | 15.41 |
| medeu | context | 25 | distance_only | 1.189e+05 | 31.54 | 49.12 | 19.35 |
| medeu | territory_osm_polygon | 25 | combined | 49 | 95.92 | 0 | 4.082 |
| medeu | territory_osm_polygon | 25 | distance_only | 49 | 95.92 | 0 | 4.082 |
| medeu | functional_footprint_derived | 25 | combined | 1.066e+04 | 57.25 | 26.14 | 16.61 |
| medeu | functional_footprint_derived | 25 | distance_only | 1.066e+04 | 57.89 | 23.48 | 18.63 |
| shymbulak | context | 7.5 | combined | 9.504e+04 | 0.8312 | 98.3 | 0.8723 |
| shymbulak | context | 7.5 | distance_only | 9.504e+04 | 1.186 | 98.12 | 0.6965 |
| shymbulak | territory_osm_polygon | 7.5 | combined | 2419 | 2.026 | 95.82 | 2.15 |
| shymbulak | territory_osm_polygon | 7.5 | distance_only | 2419 | 3.059 | 95.16 | 1.778 |
| shymbulak | functional_footprint_derived | 7.5 | combined | 2620 | 2.71 | 94.89 | 2.405 |
| shymbulak | functional_footprint_derived | 7.5 | distance_only | 2620 | 3.817 | 94.16 | 2.023 |
| shymbulak | context | 15 | combined | 9.504e+04 | 4.939 | 89.1 | 5.966 |
| shymbulak | context | 15 | distance_only | 9.504e+04 | 5.645 | 88.27 | 6.085 |
| shymbulak | territory_osm_polygon | 15 | combined | 2419 | 13.64 | 73.25 | 13.1 |
| shymbulak | territory_osm_polygon | 15 | distance_only | 2419 | 13.27 | 68.04 | 18.69 |
| shymbulak | functional_footprint_derived | 15 | combined | 2620 | 15 | 72.44 | 12.56 |
| shymbulak | functional_footprint_derived | 15 | distance_only | 2620 | 14.47 | 67.86 | 17.67 |
| shymbulak | context | 25 | combined | 9.504e+04 | 20.32 | 67.38 | 12.3 |
| shymbulak | context | 25 | distance_only | 9.504e+04 | 20.79 | 64.26 | 14.95 |
| shymbulak | territory_osm_polygon | 25 | combined | 2419 | 59.65 | 21.99 | 18.35 |
| shymbulak | territory_osm_polygon | 25 | distance_only | 2419 | 57.83 | 17.07 | 25.09 |
| shymbulak | functional_footprint_derived | 25 | combined | 2620 | 59.66 | 23.63 | 16.72 |
| shymbulak | functional_footprint_derived | 25 | distance_only | 2620 | 57.6 | 19.58 | 22.82 |
| kok_zhailau | context | 7.5 | combined | 7.409e+04 | 1.232 | 97.8 | 0.9637 |
| kok_zhailau | context | 7.5 | distance_only | 7.409e+04 | 1.518 | 97.49 | 0.9961 |
| kok_zhailau | functional_footprint_derived | 7.5 | combined | 683 | 2.782 | 93.27 | 3.953 |
| kok_zhailau | functional_footprint_derived | 7.5 | distance_only | 683 | 4.1 | 92.39 | 3.514 |
| kok_zhailau | context | 15 | combined | 7.409e+04 | 6.913 | 87.1 | 5.987 |
| kok_zhailau | context | 15 | distance_only | 7.409e+04 | 7.301 | 85.9 | 6.804 |
| kok_zhailau | functional_footprint_derived | 15 | combined | 683 | 23.72 | 58.86 | 17.42 |
| kok_zhailau | functional_footprint_derived | 15 | distance_only | 683 | 20.79 | 53.29 | 25.92 |
| kok_zhailau | context | 25 | combined | 7.409e+04 | 22.92 | 66.42 | 10.67 |
| kok_zhailau | context | 25 | distance_only | 7.409e+04 | 23.02 | 63.42 | 13.56 |
| kok_zhailau | functional_footprint_derived | 25 | combined | 683 | 64.57 | 19.18 | 16.25 |
| kok_zhailau | functional_footprint_derived | 25 | distance_only | 683 | 64.42 | 16.25 | 19.33 |
| kok_zhailau_osm | context | 7.5 | combined | 6.97e+04 | 1.89 | 96.66 | 1.452 |
| kok_zhailau_osm | context | 7.5 | distance_only | 6.97e+04 | 2.27 | 96.27 | 1.465 |
| kok_zhailau_osm | functional_footprint_derived | 7.5 | combined | 348 | 5.747 | 87.93 | 6.322 |
| kok_zhailau_osm | functional_footprint_derived | 7.5 | distance_only | 348 | 6.897 | 84.2 | 8.908 |
| kok_zhailau_osm | context | 15 | combined | 6.97e+04 | 8.751 | 83.67 | 7.576 |
| kok_zhailau_osm | context | 15 | distance_only | 6.97e+04 | 9.49 | 82.62 | 7.89 |
| kok_zhailau_osm | functional_footprint_derived | 15 | combined | 348 | 41.38 | 37.93 | 20.69 |
| kok_zhailau_osm | functional_footprint_derived | 15 | distance_only | 348 | 43.39 | 39.37 | 17.24 |
| kok_zhailau_osm | context | 25 | combined | 6.97e+04 | 29.52 | 55.73 | 14.75 |
| kok_zhailau_osm | context | 25 | distance_only | 6.97e+04 | 29.67 | 51.78 | 18.55 |
| kok_zhailau_osm | functional_footprint_derived | 25 | combined | 348 | 79.6 | 4.598 | 15.8 |
| kok_zhailau_osm | functional_footprint_derived | 25 | distance_only | 348 | 79.6 | 6.034 | 14.37 |

### Чувствительность классов к алгоритму, поддержке и выбору DEM (доля пикселей, сменивших класс)
| site | mask | threshold_deg | comparison | n | class_change_pct |
|---|---|---|---|---|---|
| medeu | context | 7.5 | algorithm horn vs zevenbergen-thorne | 1.217e+05 | 0.5587 |
| medeu | context | 7.5 | algorithm horn vs evans | 1.217e+05 | 0.1783 |
| medeu | context | 7.5 | support 30 m vs 60 m (same DEM) | 1.203e+05 | 2.565 |
| medeu | context | 7.5 | support 30 m vs 90 m (same DEM) | 1.189e+05 | 3.665 |
| medeu | context | 7.5 | DEM alos-dem vs cop-dem-glo-30 | 1.217e+05 | 1.626 |
| medeu | context | 7.5 | DEM alos-dem vs nasadem | 1.217e+05 | 2.51 |
| medeu | context | 7.5 | DEM cop-dem-glo-30 vs nasadem | 1.217e+05 | 2.029 |
| medeu | context | 15 | algorithm horn vs zevenbergen-thorne | 1.217e+05 | 1.4 |
| medeu | context | 15 | algorithm horn vs evans | 1.217e+05 | 0.4872 |
| medeu | context | 15 | support 30 m vs 60 m (same DEM) | 1.203e+05 | 7.829 |
| medeu | context | 15 | support 30 m vs 90 m (same DEM) | 1.189e+05 | 12.98 |
| medeu | context | 15 | DEM alos-dem vs cop-dem-glo-30 | 1.217e+05 | 3.733 |
| medeu | context | 15 | DEM alos-dem vs nasadem | 1.217e+05 | 6.618 |
| medeu | context | 15 | DEM cop-dem-glo-30 vs nasadem | 1.217e+05 | 5.854 |
| medeu | context | 25 | algorithm horn vs zevenbergen-thorne | 1.217e+05 | 2.616 |
| medeu | context | 25 | algorithm horn vs evans | 1.217e+05 | 0.9341 |
| medeu | context | 25 | support 30 m vs 60 m (same DEM) | 1.203e+05 | 12.8 |
| medeu | context | 25 | support 30 m vs 90 m (same DEM) | 1.189e+05 | 21.11 |
| medeu | context | 25 | DEM alos-dem vs cop-dem-glo-30 | 1.217e+05 | 6.83 |
| medeu | context | 25 | DEM alos-dem vs nasadem | 1.217e+05 | 12.9 |
| medeu | context | 25 | DEM cop-dem-glo-30 vs nasadem | 1.217e+05 | 11.74 |
| medeu | territory_osm_polygon | 7.5 | algorithm horn vs zevenbergen-thorne | 49 | 10.2 |
| medeu | territory_osm_polygon | 7.5 | algorithm horn vs evans | 49 | 2.041 |
| medeu | territory_osm_polygon | 7.5 | support 30 m vs 60 m (same DEM) | 49 | 18.37 |
| medeu | territory_osm_polygon | 7.5 | support 30 m vs 90 m (same DEM) | 49 | 24.49 |
| medeu | territory_osm_polygon | 7.5 | DEM alos-dem vs cop-dem-glo-30 | 49 | 18.37 |
| medeu | territory_osm_polygon | 7.5 | DEM alos-dem vs nasadem | 49 | 16.33 |
| medeu | territory_osm_polygon | 7.5 | DEM cop-dem-glo-30 vs nasadem | 49 | 22.45 |
| medeu | territory_osm_polygon | 15 | algorithm horn vs zevenbergen-thorne | 49 | 2.041 |
| medeu | territory_osm_polygon | 15 | algorithm horn vs evans | 49 | 0 |
| medeu | territory_osm_polygon | 15 | support 30 m vs 60 m (same DEM) | 49 | 16.33 |
| medeu | territory_osm_polygon | 15 | support 30 m vs 90 m (same DEM) | 49 | 20.41 |
| medeu | territory_osm_polygon | 15 | DEM alos-dem vs cop-dem-glo-30 | 49 | 4.082 |
| medeu | territory_osm_polygon | 15 | DEM alos-dem vs nasadem | 49 | 8.163 |
| medeu | territory_osm_polygon | 15 | DEM cop-dem-glo-30 vs nasadem | 49 | 8.163 |
| medeu | territory_osm_polygon | 25 | algorithm horn vs zevenbergen-thorne | 49 | 2.041 |
| medeu | territory_osm_polygon | 25 | algorithm horn vs evans | 49 | 2.041 |
| medeu | territory_osm_polygon | 25 | support 30 m vs 60 m (same DEM) | 49 | 4.082 |
| medeu | territory_osm_polygon | 25 | support 30 m vs 90 m (same DEM) | 49 | 6.122 |
| medeu | territory_osm_polygon | 25 | DEM alos-dem vs cop-dem-glo-30 | 49 | 0 |
| medeu | territory_osm_polygon | 25 | DEM alos-dem vs nasadem | 49 | 0 |
| medeu | territory_osm_polygon | 25 | DEM cop-dem-glo-30 vs nasadem | 49 | 0 |
| medeu | functional_footprint_derived | 7.5 | algorithm horn vs zevenbergen-thorne | 1.066e+04 | 1.378 |
| medeu | functional_footprint_derived | 7.5 | algorithm horn vs evans | 1.066e+04 | 0.5063 |
| medeu | functional_footprint_derived | 7.5 | support 30 m vs 60 m (same DEM) | 1.066e+04 | 6.395 |
| medeu | functional_footprint_derived | 7.5 | support 30 m vs 90 m (same DEM) | 1.066e+04 | 9.892 |
| medeu | functional_footprint_derived | 7.5 | DEM alos-dem vs cop-dem-glo-30 | 1.066e+04 | 5.213 |
| medeu | functional_footprint_derived | 7.5 | DEM alos-dem vs nasadem | 1.066e+04 | 7.182 |
| medeu | functional_footprint_derived | 7.5 | DEM cop-dem-glo-30 vs nasadem | 1.066e+04 | 5.401 |
| medeu | functional_footprint_derived | 15 | algorithm horn vs zevenbergen-thorne | 1.066e+04 | 2.203 |
| medeu | functional_footprint_derived | 15 | algorithm horn vs evans | 1.066e+04 | 0.6845 |
| medeu | functional_footprint_derived | 15 | support 30 m vs 60 m (same DEM) | 1.066e+04 | 13.01 |
| medeu | functional_footprint_derived | 15 | support 30 m vs 90 m (same DEM) | 1.066e+04 | 20.22 |
| medeu | functional_footprint_derived | 15 | DEM alos-dem vs cop-dem-glo-30 | 1.066e+04 | 6.423 |
| medeu | functional_footprint_derived | 15 | DEM alos-dem vs nasadem | 1.066e+04 | 10.86 |
| medeu | functional_footprint_derived | 15 | DEM cop-dem-glo-30 vs nasadem | 1.066e+04 | 9.761 |
| medeu | functional_footprint_derived | 25 | algorithm horn vs zevenbergen-thorne | 1.066e+04 | 2.579 |
| medeu | functional_footprint_derived | 25 | algorithm horn vs evans | 1.066e+04 | 0.9189 |
| medeu | functional_footprint_derived | 25 | support 30 m vs 60 m (same DEM) | 1.066e+04 | 11.16 |
| medeu | functional_footprint_derived | 25 | support 30 m vs 90 m (same DEM) | 1.066e+04 | 17.32 |
| medeu | functional_footprint_derived | 25 | DEM alos-dem vs cop-dem-glo-30 | 1.066e+04 | 8.101 |
| medeu | functional_footprint_derived | 25 | DEM alos-dem vs nasadem | 1.066e+04 | 12.23 |
| medeu | functional_footprint_derived | 25 | DEM cop-dem-glo-30 vs nasadem | 1.066e+04 | 10.46 |
| shymbulak | context | 7.5 | algorithm horn vs zevenbergen-thorne | 9.753e+04 | 0.3138 |
| shymbulak | context | 7.5 | algorithm horn vs evans | 9.753e+04 | 0.1015 |
| shymbulak | context | 7.5 | support 30 m vs 60 m (same DEM) | 9.628e+04 | 1.408 |
| shymbulak | context | 7.5 | support 30 m vs 90 m (same DEM) | 9.504e+04 | 1.95 |
| shymbulak | context | 7.5 | DEM alos-dem vs cop-dem-glo-30 | 9.753e+04 | 0.8367 |
| shymbulak | context | 7.5 | DEM alos-dem vs nasadem | 9.753e+04 | 1.394 |
| shymbulak | context | 7.5 | DEM cop-dem-glo-30 vs nasadem | 9.753e+04 | 1.282 |
| shymbulak | context | 15 | algorithm horn vs zevenbergen-thorne | 9.753e+04 | 0.9751 |
| shymbulak | context | 15 | algorithm horn vs evans | 9.753e+04 | 0.3322 |
| shymbulak | context | 15 | support 30 m vs 60 m (same DEM) | 9.628e+04 | 5.09 |
| shymbulak | context | 15 | support 30 m vs 90 m (same DEM) | 9.504e+04 | 8.322 |
| shymbulak | context | 15 | DEM alos-dem vs cop-dem-glo-30 | 9.753e+04 | 2.667 |
| shymbulak | context | 15 | DEM alos-dem vs nasadem | 9.753e+04 | 4.757 |
| shymbulak | context | 15 | DEM cop-dem-glo-30 vs nasadem | 9.753e+04 | 4.362 |
| shymbulak | context | 25 | algorithm horn vs zevenbergen-thorne | 9.753e+04 | 1.823 |
| shymbulak | context | 25 | algorithm horn vs evans | 9.753e+04 | 0.6696 |
| shymbulak | context | 25 | support 30 m vs 60 m (same DEM) | 9.628e+04 | 9.788 |
| shymbulak | context | 25 | support 30 m vs 90 m (same DEM) | 9.504e+04 | 17.02 |
| shymbulak | context | 25 | DEM alos-dem vs cop-dem-glo-30 | 9.753e+04 | 5.465 |
| shymbulak | context | 25 | DEM alos-dem vs nasadem | 9.753e+04 | 10.6 |
| shymbulak | context | 25 | DEM cop-dem-glo-30 vs nasadem | 9.753e+04 | 10.06 |
| shymbulak | territory_osm_polygon | 7.5 | algorithm horn vs zevenbergen-thorne | 2419 | 0.5374 |
| shymbulak | territory_osm_polygon | 7.5 | algorithm horn vs evans | 2419 | 0.08268 |
| shymbulak | territory_osm_polygon | 7.5 | support 30 m vs 60 m (same DEM) | 2419 | 2.687 |
| shymbulak | territory_osm_polygon | 7.5 | support 30 m vs 90 m (same DEM) | 2419 | 4.217 |
| shymbulak | territory_osm_polygon | 7.5 | DEM alos-dem vs cop-dem-glo-30 | 2419 | 1.984 |
| shymbulak | territory_osm_polygon | 7.5 | DEM alos-dem vs nasadem | 2419 | 3.597 |
| shymbulak | territory_osm_polygon | 7.5 | DEM cop-dem-glo-30 vs nasadem | 2419 | 4.093 |
| shymbulak | territory_osm_polygon | 15 | algorithm horn vs zevenbergen-thorne | 2419 | 2.15 |
| shymbulak | territory_osm_polygon | 15 | algorithm horn vs evans | 2419 | 1.116 |
| shymbulak | territory_osm_polygon | 15 | support 30 m vs 60 m (same DEM) | 2419 | 11.16 |
| shymbulak | territory_osm_polygon | 15 | support 30 m vs 90 m (same DEM) | 2419 | 15.71 |
| shymbulak | territory_osm_polygon | 15 | DEM alos-dem vs cop-dem-glo-30 | 2419 | 5.209 |
| shymbulak | territory_osm_polygon | 15 | DEM alos-dem vs nasadem | 2419 | 10.33 |
| shymbulak | territory_osm_polygon | 15 | DEM cop-dem-glo-30 vs nasadem | 2419 | 10.25 |
| shymbulak | territory_osm_polygon | 25 | algorithm horn vs zevenbergen-thorne | 2419 | 2.852 |
| shymbulak | territory_osm_polygon | 25 | algorithm horn vs evans | 2419 | 0.8268 |
| shymbulak | territory_osm_polygon | 25 | support 30 m vs 60 m (same DEM) | 2419 | 12.28 |
| shymbulak | territory_osm_polygon | 25 | support 30 m vs 90 m (same DEM) | 2419 | 18.69 |
| shymbulak | territory_osm_polygon | 25 | DEM alos-dem vs cop-dem-glo-30 | 2419 | 6.573 |
| shymbulak | territory_osm_polygon | 25 | DEM alos-dem vs nasadem | 2419 | 13.31 |
| shymbulak | territory_osm_polygon | 25 | DEM cop-dem-glo-30 vs nasadem | 2419 | 11.86 |
| shymbulak | functional_footprint_derived | 7.5 | algorithm horn vs zevenbergen-thorne | 2620 | 0.9924 |
| shymbulak | functional_footprint_derived | 7.5 | algorithm horn vs evans | 2620 | 0.229 |
| shymbulak | functional_footprint_derived | 7.5 | support 30 m vs 60 m (same DEM) | 2620 | 3.244 |
| shymbulak | functional_footprint_derived | 7.5 | support 30 m vs 90 m (same DEM) | 2620 | 5.267 |
| shymbulak | functional_footprint_derived | 7.5 | DEM alos-dem vs cop-dem-glo-30 | 2620 | 2.176 |
| shymbulak | functional_footprint_derived | 7.5 | DEM alos-dem vs nasadem | 2620 | 4.122 |
| shymbulak | functional_footprint_derived | 7.5 | DEM cop-dem-glo-30 vs nasadem | 2620 | 4.237 |
| shymbulak | functional_footprint_derived | 15 | algorithm horn vs zevenbergen-thorne | 2620 | 2.137 |
| shymbulak | functional_footprint_derived | 15 | algorithm horn vs evans | 2620 | 1.107 |
| shymbulak | functional_footprint_derived | 15 | support 30 m vs 60 m (same DEM) | 2620 | 10.31 |
| shymbulak | functional_footprint_derived | 15 | support 30 m vs 90 m (same DEM) | 2620 | 16.18 |
| shymbulak | functional_footprint_derived | 15 | DEM alos-dem vs cop-dem-glo-30 | 2620 | 4.924 |
| shymbulak | functional_footprint_derived | 15 | DEM alos-dem vs nasadem | 2620 | 10.34 |
| shymbulak | functional_footprint_derived | 15 | DEM cop-dem-glo-30 vs nasadem | 2620 | 10.15 |
| shymbulak | functional_footprint_derived | 25 | algorithm horn vs zevenbergen-thorne | 2620 | 2.634 |
| … ещё 90 строк в CSV | | | | | |

## 6. Международное сравнение (статистики рельефа окон; не отождествление курортов)
| site | group | country | boundary_status | reference_dtm | elev_min_m | elev_p5_m | elev_p95_m | elev_max_m | relief_p95_p5_m | area_km2 | mean_slope | share_lt_7.5 | share_7.5_15 | share_15_25 | share_ge_25 | mean_dem_slope_std_deg | abstain_pct_t7.5 | abstain_pct_t15 | abstain_pct_t25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| medeu | kazakhstan | KZ | OSM_POLYGON_NAMED_MATCH | False | 1074 | 1292 | 2864 | 3461 | 1572 | 109.5 | 26.05 | 3.874 | 10.07 | 26.8 | 59.26 | 1.781 | 1.487 | 7.996 | 15.41 |
| shymbulak | kazakhstan | KZ | OSM_POLYGON_NAMED_MATCH | False | 1420 | 1712 | 3584 | 4275 | 1872 | 87.78 | 29.53 | 1.549 | 6.939 | 19.01 | 72.5 | 1.915 | 0.8723 | 5.966 | 12.3 |
| kok_zhailau | kazakhstan | KZ | FUNCTIONAL_FOOTPRINT_ONLY | False | 1828 | 2130 | 3693 | 4092 | 1563 | 68.66 | 29.15 | 2.016 | 8.565 | 18.54 | 70.88 | 1.779 | 0.9637 | 5.987 | 10.67 |
| kok_zhailau_osm | kazakhstan | KZ | FUNCTIONAL_FOOTPRINT_ONLY | False | 1240 | 1407 | 3011 | 3318 | 1604 | 64.64 | 26.59 | 3.039 | 10.16 | 24.94 | 61.86 | 1.778 | 1.452 | 7.576 | 14.75 |
| davos_parsenn | validation | CH | OSM_POLYGON_NAMED_MATCH | True | 1299 | 1569 | 2532 | 2826 | 963.1 | 83.17 | 22.35 | 7.764 | 17.85 | 34.24 | 40.14 | 1.532 | 2.097 | 10.45 | 14.72 |
| zermatt_gornergrat | validation | CH | OSM_POLYGON_NAMED_MATCH | True | 1588 | 1831 | 3113 | 3445 | 1282 | 84.82 | 23.32 | 11.15 | 17.76 | 26.87 | 44.22 | 1.863 | 3.483 | 10.07 | 12.68 |
| alta_snowbird | validation | US | OSM_POLYGON_NAMED_MATCH | True | 2249 | 2489 | 3227 | 3492 | 738.1 | 83.17 | 25.33 | 4.496 | 14.23 | 29.21 | 52.07 | 1.702 | 1.766 | 9.05 | 13.21 |
| park_city | validation | US | OSM_POLYGON_NAMED_MATCH | True | 1962 | 2033 | 2835 | 3056 | 802.7 | 83.17 | 15.2 | 24.01 | 24.93 | 36.03 | 15.03 | 1.122 | 3.073 | 11.48 | 10.59 |
| kazakhstan_site | comparison_site | country | terrain_stat_distance |
|---|---|---|---|
| kok_zhailau | zermatt_gornergrat | CH | 2.576 |
| kok_zhailau | alta_snowbird | US | 3.097 |
| kok_zhailau | davos_parsenn | CH | 3.867 |
| kok_zhailau | park_city | US | 5.757 |
| kok_zhailau_osm | zermatt_gornergrat | CH | 1.537 |
| kok_zhailau_osm | alta_snowbird | US | 2.401 |
| kok_zhailau_osm | davos_parsenn | CH | 2.763 |
| kok_zhailau_osm | park_city | US | 4.669 |
| medeu | zermatt_gornergrat | CH | 1.294 |
| medeu | alta_snowbird | US | 2.202 |
| medeu | davos_parsenn | CH | 2.429 |
| medeu | park_city | US | 4.355 |
| shymbulak | zermatt_gornergrat | CH | 2.947 |
| shymbulak | alta_snowbird | US | 3.686 |
| shymbulak | davos_parsenn | CH | 4.261 |
| shymbulak | park_city | US | 6.123 |

## 7. Незавершённое и причины
| site | source | status | details |
|---|---|---|---|
| all | KazEOSat-1/2 | MANUAL_LICENSE_REQUIRED | no public anonymous catalogue of KazEOSat scenes found; official request draft in KAZEOSAT_REQUEST_RU.md |
