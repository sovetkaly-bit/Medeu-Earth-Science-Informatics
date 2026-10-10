# R40 Kazakhstan — Support-Aware Terrain Threshold Decisions

Воспроизводимый проект для статьи (Earth Science Informatics): надёжность пороговых решений об уклонах (7,5° / 15° / 25°) и решения **BELOW / ABOVE / ABSTAIN**. Центральный прикладной пример — Медеу, Шымбулак, Кок-Жайлау (Алматы).

## Запуск
GitHub → **Actions → «R40 Kazakhstan — all available satellite and elevation sources» → Run workflow**. Результат — единый архив `R40-Kazakhstan-results` (Artifacts) и копия в ветке `r40-results` (читается без скачивания).
Локально: `cd research/R40_KZ && pip install -r requirements.txt && python -m unittest discover -s tests && python -m src.run`.

## Структура
* `src/boundaries.py` — геометрии из OpenStreetMap (Overpass/Nominatim) с происхождением; никаких «квадратов вместо границ».
* `src/sources.py` — Copernicus GLO-30, NASADEM, ALOS World 3D-30 (Planetary Computer), FABDEM (попытка), эталоны: swissALTI3D (2 м, Швейцария) и USGS 3DEP (10 м, США).
* `src/terrain.py` — уклон (Horn, Zevenbergen–Thorne, Evans), агрегирование, признаки решения.
* `src/decision.py`, `src/experiment.py` — эксперимент R40: расстояние до порога, расхождение DEM, локальная изменчивость, устойчивость к масштабу, комбинированная модель; risk–coverage, AURC, калибровка, блочный bootstrap, LOSO, стресс-тесты.
* `src/optical.py` — каталоги Sentinel-1/2, Landsat C2; NDVI-превью с маской облаков/снега (диагностика). KazEOSat — только ручной лицензируемый запрос (`KAZEOSAT_REQUEST_RU.md`).
* `tests/` — офлайн-тесты на синтетическом рельефе (запускаются в workflow перед расчётом).

## Принципы
* Эталонная DTM для Казахстана в открытом доступе не найдена → качество для Казахстана **не измеряется**, а переносится с независимых территорий (Швейцария/США) и так маркируется.
* Согласие двух глобальных DEM не считается независимым подтверждением (проверяется на эталоне).
* Данные с ограничивающими лицензиями (ALOS, FABDEM, KazEOSat) в публичный репозиторий не включаются.
* Утверждённая авторская концепция не меняется автоматически; расхождения (например, положение Кок-Жайлау в OSM) выносятся как отдельные варианты.
* `src/legacy_pilot.py` — исходный пилотный скрипт из присланного архива, не используется.
