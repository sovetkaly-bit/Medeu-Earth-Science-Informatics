# Almaty snow and precipitation: satellite and gridded products

Purpose: independent check of seasonality in the northern Ile Alatau (Almaty city to ridge) for a monograph climate section.

Sources (all read anonymously from Microsoft Planetary Computer, no secrets required):
- MODIS Terra MOD10A1 v061 daily snow cover (NASA NSIDC DAAC product, COG mirror), 2000 onward. Satellite retrieval; clouds are excluded from the denominator.
- Copernicus GLO-30 DEM for the elevation bands.
- TerraClimate monthly precipitation, SWE, Tmax, Tmin (gridded model product, not station measurements).

Not included in this run: GPM IMERG and ERA5-Land (need Earthdata/CDS credentials); Aqua MYD10A1 (not in the mirror).

Definitions (config.json): snow = NDSI >= 40; a day is valid if at least 30 percent of band pixels are clear; snow state if snow share of clear pixels >= 0.5; onset and end = first and last run of >= 3 consecutive valid snow-state observations spanning >= 10 days (cloud gaps do not break a run); a season (1 Sep - 31 May) is accepted if valid days >= 50 percent of its days. Trends: Theil-Sen with 95 percent interval and Mann-Kendall p (Kendall tau), minimum 10 accepted seasons, no serial-correlation adjustment.

Run: workflow `Almaty snow satellite` (push to branch almaty-climate-snow or manual dispatch). Outputs: artifact `ALMATY_SNOW_SATELLITE_PACKAGE` and branch `almaty-snow-results`.
Rebuild offline from the stored CSV: `python -m src.analyze`.
