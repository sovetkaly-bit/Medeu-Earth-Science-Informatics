# Earth Science Informatics — R40 Kazakhstan, single-run satellite/elevation acquisition

**Purpose:** one execution covering Shymbulak, Medeu, Kok-Zhailau (provisional *centered square* AOIs, NOT resort boundaries). Script discovers Sentinel-2, Landsat Collection 2, Sentinel-1 GRD and elevation products Copernicus GLO-30, ALOS DEM, NASADEM in Microsoft Planetary Computer STAC. It checks Sentinel-2 availability independently through Copernicus Data Space STAC. Where authenticated public COG access works it obtains 30-m aligned cropped DEM rasters and produces slope maps, threshold counts (7.5,15,25°) and pairwise disagreement on common valid pixels. No external actions are necessary beyond starting GitHub Actions.

## Run
1. Create/open a GitHub repository with GitHub Actions enabled. Upload **contents of this folder to the repository root**, including `.github/workflows/r40_kz_all_sources.yml` (GitHub browser file upload may skip hidden `.github`; check it carefully).
2. Open **Actions → R40 Kazakhstan — all available satellite and elevation sources → Run workflow → all**.
3. When complete, click workflow run → **Artifacts → R40-Kazakhstan-multisource-results**; download the ZIP and upload it in the ChatGPT research conversation.
4. Inspect `run_status.csv` and `manifest.json` first. A successful workflow does NOT imply each source was downloadable.

## Scientific restrictions
- KazEOSat-1 (~1 m) and KazEOSat-2 (~6.5 m): **manual acquisition/license**, no public anonymous raw scene API presumed. See `KAZEOSAT_REQUEST_RU.md`.
- JAXA official AW3D30 requires **registered download**. `alos-dem` in Planetary Computer is a distinct STAC offering whose identity/coverage must be independently checked; do not label it AW3D30 without verifying metadata. See https://www.eorc.jaxa.jp/ALOS/en/dataset/aw3d30/aw3d30_e.htm .
- Copernicus, ALOS and NASADEM elevation assets are *not validated independent bare-earth reference DTM*. Pairwise model disagreement **is not accuracy**, slopes computed from 30-m DEM are not engineering suitability judgments.
- Sentinel-1 scenes are catalogued; Sentinel-2/Landsat are catalogued AND their red/NIR raster snippets are requested to produce exploratory NDVI GeoTIFFs when accessible. NDVI rasters are **not cloud/snow masked**, and Sentinel-2 processing-baseline offsets can bias results; these are diagnostic previews only, not validated vegetation estimates. Seasonal composites, proper per-pixel QA, and reflectance correction require a later stage.
- For journal-ready R40: independent high-resolution DTM, ground truth masked comparisons, slope errors, leakage-resistant spatial blocks, nested calibration, baselines, AURC and risk–coverage still needed.
- Provisional center coordinates come from the working research record and must be replaced by official resort/area polygons.

## Sources
- https://planetarycomputer.microsoft.com/api/stac/v1
- https://stac.dataspace.copernicus.eu/v1/
- https://www.eorc.jaxa.jp/ALOS/en/dataset/aw3d30/aw3d30_e.htm

## Run outputs
`run_status.csv` source-by-source outcome; `site/catalog/*.json` scene metadata; `site/rasters/*.tif` where available; `site/slope_counts.csv`; `site/pairwise_disagreement.csv`; `site/figures/*.png`; `manifest.json`; `sha256.txt`.
