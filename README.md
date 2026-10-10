# R40 — Support-Aware Terrain Threshold Decisions: Kazakhstan (Medeu · Shymbulak · Kok-Zhailau)

Run label: **R40-KZ-2026-10** · finished (UTC): 2026-10-10T14:24:39+00:00
Workflow run: https://github.com/sovetkaly-bit/Medeu-Earth-Science-Informatics/actions/runs/38058021115 · commit: https://github.com/sovetkaly-bit/Medeu-Earth-Science-Informatics/commit/42d2dee2ef358535245408df9b462996c102bac8

## Что это
Воспроизводимый архив одного запуска: границы территорий (OpenStreetMap), цифровые модели рельефа (Copernicus GLO-30, NASADEM, ALOS, FABDEM — если удалось получить),
независимые эталонные DTM для валидации (swissALTI3D в Швейцарии, USGS 3DEP в США), решения BELOW / ABOVE / ABSTAIN для порогов [7.5, 15, 25]° и результаты по Казахстану.

## Главное ограничение
Для Казахстана **независимой эталонной DTM нет** (не найдено в открытом доступе). Поэтому:
* ошибка классификации уклонов в Казахстане **не измерена**; показатели качества получены на независимых территориях (Швейцария, США) и **перенесены** на Казахстан как модель неопределённости;
* согласие двух глобальных DEM не считается независимым подтверждением (см. `tables/validation_shared_error_consensus.csv`);
* категория уклона не является разрешением на строительство: геотехнические, сейсмические, водные, экологические и инфраструктурные ограничения не учитывались.

## Содержимое
* `REPORT.md` — таблицы результатов; `tables/*.csv` — все числа; `figures/*.png` — карты и графики;
* `sites/<site>/rasters/*.tif` — GeoTIFF (UTM, 30 м); `sites/<site>/decision_*.geojson` — решения в векторе; `boundaries/*.geojson` — геометрии с происхождением (`*_provenance.json`, `*_candidates.json`);
* `sites/<site>/sources_provenance.json` — ссылки на исходные данные (STAC items / URL) для воспроизведения; `sites/<site>/catalog/*.json` — каталоги Sentinel-1/2, Landsat;
* `run_status.csv`, `errors.json` — журнал источников и ошибок; `manifest.json`; `sha256.txt` — контрольные суммы SHA-256 всех файлов;
* `code/` — исходный код, конфигурация и тесты этого запуска.

## Лицензии и атрибуция
Copernicus DEM GLO-30: © DLR e.V. 2010–2014 и © Airbus Defence and Space GmbH 2014–2018, предоставлено по программе COPERNICUS (ЕС и ESA). NASADEM: NASA (общественное достояние).
USGS 3DEP: общественное достояние. swissALTI3D: © swisstopo (OGD). OpenStreetMap: © участники OpenStreetMap, ODbL.
**ALOS (JAXA) и FABDEM (CC BY-NC-SA 4.0)**: растры в архив не включены, только производная статистика; получаются повторным запуском. KazEOSat-1/2: лицензируемые данные, не загружались и не распространяются.

## Воспроизведение
GitHub → Actions → «R40 Kazakhstan — all available satellite and elevation sources» → Run workflow; либо локально: `cd research/R40_KZ && pip install -r requirements.txt && python -m unittest discover -s tests && python -m src.run`.
Версии зависимостей фиксируются диапазонами в `requirements.txt`; реально использованная версия Python — в `manifest.json`.

## Статус источников в этом запуске
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

