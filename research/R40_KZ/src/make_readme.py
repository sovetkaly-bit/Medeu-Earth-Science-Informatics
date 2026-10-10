"""Generate README.md and REPORT.md inside the output archive (numbers are read back from the CSV tables)."""
from __future__ import annotations
import csv, os
from pathlib import Path
from . import common as C
from .report import md_table


def _rd(p):
    p = Path(p)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return rows


def _run_ref():
    repo, rid, sha = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_RUN_ID"), os.environ.get("GITHUB_SHA")
    if repo and rid:
        return {"run_url": f"https://github.com/{repo}/actions/runs/{rid}", "commit": f"https://github.com/{repo}/commit/{sha}", "sha": sha}
    return {"run_url": "local run", "commit": "n/a", "sha": None}


def write_readme(out, cfg, data, results, manifest_val):
    tb = Path(out) / "tables"
    ref = _run_ref()
    status = {}
    for r in C.AUDIT:
        status[(r["site"], r["source"])] = r["status"]
    src_rows = [{"site": s, "source": src, "status": st} for (s, src), st in sorted(status.items()) if src != "timing"]
    C.write_csv(Path(out) / "tables" / "sources_status_summary.csv", src_rows)

    readme = f"""# R40 — Support-Aware Terrain Threshold Decisions: Kazakhstan (Medeu · Shymbulak · Kok-Zhailau)

Run label: **{cfg['run_label']}** · finished (UTC): {C.now()}
Workflow run: {ref['run_url']} · commit: {ref['commit']}

## Что это
Воспроизводимый архив одного запуска: границы территорий (OpenStreetMap), цифровые модели рельефа (Copernicus GLO-30, NASADEM, ALOS, FABDEM — если удалось получить),
независимые эталонные DTM для валидации (swissALTI3D в Швейцарии, USGS 3DEP в США), решения BELOW / ABOVE / ABSTAIN для порогов {cfg['thresholds_deg']}° и результаты по Казахстану.

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
{md_table(src_rows, ['site', 'source', 'status'], max_rows=200)}
"""
    (Path(out) / "README.md").write_text(readme, encoding="utf-8")

    th = cfg["thresholds_deg"]
    aurc = [r for r in _rd(tb / "validation_aurc.csv") if r["site"] == "POOLED" and r["scheme"] == "loso"]
    ci = [r for r in _rd(tb / "validation_aurc_bootstrap_ci.csv") if r["scheme"] == "loso"]
    parts = ["# R40 — отчёт запуска (числа считаны из tables/*.csv)\n"]
    parts.append("## 1. Какие данные реально получены\n" + md_table([r for r in src_rows if r["status"] not in ("ACQUIRE_DONE",)], ["site", "source", "status"], max_rows=200))
    parts.append("## 2. Границы территорий\n" + md_table([{"site": k, "boundary_status": d["boundary_status"], "reference_dtm": d.get("ref_fine") is not None, "dems": ", ".join(sorted(d["z"]))} for k, d in data.items()]))
    parts.append("## 3. Контроль DEM\n" + md_table(_rd(tb / "dem_qc.csv"), ["site", "dem", "valid_px", "nodata_pct", "min_m", "max_m", "vertical_datum", "type"], max_rows=80))
    parts.append("## 4. Валидация (LOSO: обучение на других территориях, оценка на удержанной)\nAURC — площадь под кривой risk–coverage (меньше = лучше). random = доля ошибок без отказов.\n")
    for t in th:
        rows = [r for r in aurc if r["threshold_deg"] == t]
        crow = {r["method"]: r for r in ci if r["threshold_deg"] == t}
        for r in rows:
            c = crow.get(r["method"], {})
            r["AURC_95CI"] = f"[{c.get('AURC_lo95', float('nan')):.4f}; {c.get('AURC_hi95', float('nan')):.4f}]" if c else "—"
            r["dAURC_vs_distance_95CI"] = f"[{c.get('dAURC_lo95', float('nan')):+.4f}; {c.get('dAURC_hi95', float('nan')):+.4f}]" if c else "—"
        parts.append(f"### Порог {t}°\n" + md_table(rows, ["method", "n_pixels", "AURC", "AURC_95CI", "dAURC_vs_distance_95CI", "E_AURC", "risk@0.90", "risk@0.70"]))
    parts.append("### Калибровка комбинированной модели (LOSO)\n" + md_table(_rd(tb / "validation_calibration_metrics.csv")))
    parts.append("### Рабочие точки: порог неопределённости зафиксирован на обучающих территориях, оценка на удержанной\n" + md_table(_rd(tb / "validation_operating_points_heldout.csv"), ["threshold_deg", "heldout_site", "method", "target_risk_train", "coverage_heldout", "selective_risk_heldout", "full_coverage_error_heldout"], max_rows=120))
    parts.append("### Стресс-тесты (AURC, pooled LOSO)\n" + md_table(_rd(tb / "validation_stress_tests.csv"), None, max_rows=60))
    parts.append("### Ошибка глобальных DEM относительно независимой эталонной DTM\n" + md_table(_rd(tb / "validation_dem_error_vs_reference.csv")))
    parts.append("### Согласие DEM как «подтверждение»?\n" + md_table(_rd(tb / "validation_shared_error_consensus.csv")))
    parts.append("## 5. Казахстан: решения (ошибка не измерена, модель перенесена)\n" + md_table([r for r in _rd(tb / "decisions_by_site.csv") if r.get("group") == "kazakhstan"], ["site", "mask", "threshold_deg", "method", "n_px", "BELOW_pct", "ABOVE_pct", "ABSTAIN_pct"], max_rows=80))
    parts.append("### Чувствительность классов к алгоритму, поддержке и выбору DEM (доля пикселей, сменивших класс)\n" + md_table(_rd(tb / "kazakhstan_sensitivity_class_change.csv"), ["site", "mask", "threshold_deg", "comparison", "n", "class_change_pct"], max_rows=120))
    parts.append("## 6. Международное сравнение (статистики рельефа окон; не отождествление курортов)\n" + md_table(_rd(tb / "international_comparison.csv"), None, max_rows=20) + md_table(_rd(tb / "international_terrain_similarity.csv"), ["kazakhstan_site", "comparison_site", "country", "terrain_stat_distance"], max_rows=30))
    unfinished = [r for r in C.AUDIT if r["status"] not in ("RASTER_READY", "REFERENCE_READY", "FOUND", "NDVI_READY", "OSM_POLYGON_NAMED_MATCH", "FUNCTIONAL_FOOTPRINT_ONLY", "CATALOG_OK", "VALIDATION_DONE", "ACQUIRE_DONE")]
    parts.append("## 7. Незавершённое и причины\n" + md_table([{"site": r["site"], "source": r["source"], "status": r["status"], "details": r["details"][:160]} for r in unfinished], ["site", "source", "status", "details"], max_rows=120))
    (Path(out) / "REPORT.md").write_text("\n".join(parts), encoding="utf-8")
