"""R40 Kazakhstan: discover Sentinel-2, retrieve Copernicus DSM COG tile,
calculate illustrative slope classes. NOT an independent accuracy validation.
"""
import argparse, csv, json, hashlib, os, requests
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds, transform as window_transform
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds

SITES = {
 'shymbulak': (77.08142,43.12827),
 'medeu': (77.0584,43.1577),
 'kok_zhailau': (77.055,43.105),
}
ROOT=Path('output'); ROOT.mkdir(exist_ok=True)

def write_json(name,obj): (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def get_copernicus_cog(lon,lat):
 # 1-degree tile identifier, SW corner convention; AWS public GLO-30 DSM
 from math import floor
 slat=floor(lat);slon=floor(lon)
 latcode=('N' if slat>=0 else 'S')+f'{abs(slat):02d}_00'
 loncode=('E' if slon>=0 else 'W')+f'{abs(slon):03d}_00'
 name=f'Copernicus_DSM_COG_10_{latcode}_{loncode}_DEM'
 return f'https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/{name}/{name}.tif'

def query_sentinel(site,lon,lat):
 # Search only; no claim of pixel ingestion. STAC catalog supports GET /search.
 eps=.06
 params={'collections':'sentinel-2-l2a','bbox':f'{lon-eps},{lat-eps},{lon+eps},{lat+eps}',
         'datetime':'2025-06-01T00:00:00Z/2025-09-30T23:59:59Z','limit':20}
 url='https://stac.dataspace.copernicus.eu/v1/search'
 try:
  rsp=requests.get(url,params=params,timeout=60);rsp.raise_for_status();data=rsp.json()
  features=data.get('features',[])
  slim=[]
  for x in features:
   pp=x.get('properties',{})
   slim.append({'id':x.get('id'),'date':pp.get('datetime'),
                'cloud_cover':pp.get('eo:cloud_cover'),
                'assets':list(x.get('assets',{}).keys())})
  write_json(f'{site}_sentinel_search.json',{'endpoint':url,'params':params,'items':slim,'count_returned':len(slim)})
 except Exception as exc:write_json(f'{site}_sentinel_search_ERROR.json',{'endpoint':url,'error':str(exc)})

def handle_terrain(site,lon,lat):
 url=get_copernicus_cog(lon,lat);write_json(f'{site}_cop_source.json',{'source':url,'type':'DSM','reference_DTM':False})
 try:
  # Read a small cropped window remotely through GDAL/rasterio range requests.
  with rasterio.Env(GDAL_HTTP_MAX_RETRY='2',GDAL_HTTP_RETRY_DELAY='2'):
   with rasterio.open(url) as ds:
    box=(lon-.065,lat-.055,lon+.065,lat+.055)
    win=from_bounds(*box,transform=ds.transform).round_offsets().round_lengths()
    band=ds.read(1,window=win,masked=True)
    wt=window_transform(win,ds.transform)
    meta=ds.meta.copy();meta.update(height=band.shape[0],width=band.shape[1],transform=wt,compress='deflate')
    local=ROOT/f'{site}_cop30_DSM_crop.tif'
    with rasterio.open(local,'w',**meta) as out:out.write(band.filled(ds.nodata or -32767),1)
   # Resample to 30m projected metric grid, using common CRS UTM 43N (EPSG:32643)
   with rasterio.open(local) as src:
    dst_crs='EPSG:32643'
    tf,w,h=calculate_default_transform(src.crs,dst_crs,src.width,src.height,*src.bounds,resolution=30)
    dst=np.full((h,w),np.nan,dtype='float32')
    reproject(rasterio.band(src,1),dst,src_transform=src.transform,src_crs=src.crs,
              src_nodata=src.nodata,dst_transform=tf,dst_crs=dst_crs,
              dst_nodata=np.nan,resampling=Resampling.bilinear)
   gy,gx=np.gradient(dst,30.,30.)
   slope=np.rad2deg(np.arctan(np.hypot(gx,gy)))
   valid=np.isfinite(slope)
   # Exclude one-cell external perimeter to avoid gradient boundary artefacts.
   valid[[0,-1],:]=False;valid[:,[0,-1]]=False
   rows=[]
   for t in [7.5,15.0,25.0]:
    n=int(valid.sum());below=int(np.sum(valid&(slope<t)));above=int(np.sum(valid&(slope>=t)))
    rows.append({'site':site,'model':'Copernicus GLO-30 DSM','threshold_deg':t,
                 'valid_pixels':n,'below':below,'above':above,'abstain':'NOT_EVALUATED',
                 'validation':'NO_REFERENCE_DTM','status':'ILLUSTRATIVE_ONLY'})
   with open(ROOT/f'{site}_terrain_summary.csv','w',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=rows[0]);wr.writeheader();wr.writerows(rows)
   write_json(f'{site}_terrain_provenance.json',{'url':url,'local_sha256':sha256(local),
               'projected_crs':dst_crs,'working_grid_m':30,'caution':'DSM slope is not bare-earth slope; independent DTM required.'})
 except Exception as exc:write_json(f'{site}_terrain_ERROR.json',{'url':url,'error':str(exc)})

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--site',choices=[*SITES,'all'],default='all');args=ap.parse_args()
 sites=SITES if args.site=='all' else {args.site:SITES[args.site]}
 for site,(lon,lat) in sites.items():
  query_sentinel(site,lon,lat);handle_terrain(site,lon,lat)
  print(site,'processed; see output/ for errors or results')
