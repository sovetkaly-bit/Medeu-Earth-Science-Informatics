"""R40 KZ. Multi-source discover + DEM grid + slope and agreement diagnostics.
Never invent access to commercial imagery or claim an independent reference DTM.
"""
import argparse, csv, hashlib, json, math, os, traceback
from pathlib import Path
import numpy as np
import requests
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from pyproj import Transformer

ROOT=Path('output'); ROOT.mkdir(exist_ok=True)
CFG=json.loads(Path('config.json').read_text())
AUDIT=[]
def log(site,source,status,detail='',n=None):
    AUDIT.append(dict(site=site,source=source,status=status,details=str(detail)[:1500],count=n))
    print(f'[{site}] {source}: {status} {detail}',flush=True)
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()
def bbox(lon,lat,rkm):
    dy=rkm/111.1;dx=rkm/(111.1*math.cos(math.radians(lat)))
    return [lon-dx,lat-dy,lon+dx,lat+dy]
def target_grid(b):
    trans=Transformer.from_crs('EPSG:4326',CFG['grid_crs'],always_xy=True)
    x0,y0=trans.transform(b[0],b[1]);x1,y1=trans.transform(b[2],b[3]);rs=CFG['grid_resolution_m']
    xlow,xhigh=min(x0,x1),max(x0,x1);ylow,yhigh=min(y0,y1),max(y0,y1)
    w=math.ceil((xhigh-xlow)/rs);h=math.ceil((yhigh-ylow)/rs)
    return from_origin(xlow,yhigh,rs,rs),(h,w)
def search(client,collection,b,site):
    try:
        kwargs={'collections':[collection], 'bbox':b,'max_items':CFG['max_items_per_collection']}
        if collection in ('sentinel-2-l2a','landsat-c2-l2','sentinel-1-grd'):kwargs['datetime']=CFG['optical_dates']
        items=list(client.search(**kwargs).items())
        if collection in ('sentinel-2-l2a','landsat-c2-l2'):
            items.sort(key=lambda v:(v.properties.get('eo:cloud_cover') if isinstance(v.properties.get('eo:cloud_cover'),(int,float)) else 1000))
        slim=[]
        for x in items:
            slim.append({'id':x.id,'datetime':x.properties.get('datetime'),'cloud_cover':x.properties.get('eo:cloud_cover'),
               'bbox':x.bbox,'asset_keys':list(x.assets.keys()),'collection':collection})
        write(ROOT/site/'catalog'/f'{collection}.json',slim)
        log(site,collection,'FOUND' if items else 'NO_ITEMS','catalog results',len(items))
        return items
    except Exception as e:
        log(site,collection,'SEARCH_FAILED',e);return []
def select_asset(item,collection):
    keys={'cop-dem-glo-30':['data'],'alos-dem':['data'],'nasadem':['elevation'],'sentinel-2-l2a':['B04','B03','B02','B08','red','green','blue','nir'],
          'landsat-c2-l2':['red','green','blue','nir08','SR_B4','SR_B3','SR_B2','SR_B5']}.get(collection,[])
    for k in keys:
        if k in item.assets:return k,item.assets[k].href
    return None,None
def warp_asset(url,transform,shape,resampling):
    arr=np.full(shape,np.nan,dtype='float32')
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_HTTP_MAX_RETRY='3',GDAL_HTTP_RETRY_DELAY='2'):
        with rasterio.open(url) as src:
            reproject(source=rasterio.band(src,1),destination=arr,src_transform=src.transform,src_crs=src.crs,
                      src_nodata=src.nodata,dst_transform=transform,dst_crs=CFG['grid_crs'],
                      dst_nodata=np.nan,resampling=resampling)
    return arr
def save_tiff(p,array,transform,nodata=np.nan):
    p.parent.mkdir(parents=True,exist_ok=True)
    with rasterio.open(p,'w',driver='GTiff',height=array.shape[0],width=array.shape[1],count=1,
          dtype='float32',crs=CFG['grid_crs'],transform=transform,nodata=nodata,compress='deflate') as out:out.write(array.astype('float32'),1)
def slope_deg(a):
    rs=CFG['grid_resolution_m']
    # Mask erosion avoids differentiating across nodata holes.
    valid=np.isfinite(a)
    core=valid.copy()
    for shift,axis in ((1,0),(-1,0),(1,1),(-1,1)):
        core &= np.roll(valid,shift,axis)
    core[[0,-1],:]=False;core[:,[0,-1]]=False
    v=np.where(valid,a,0.0)
    gy,gx=np.gradient(v,float(rs),float(rs));s=np.degrees(np.arctan(np.hypot(gx,gy)))
    return np.where(core,s,np.nan).astype('float32')
def terrain(site,items,b):
    transform,shape=target_grid(b)
    slopes={};stats=[]
    for collection in ('cop-dem-glo-30','alos-dem','nasadem'):
        if not items.get(collection):continue
        it=items[collection][0]
        key,url=select_asset(it,collection)
        if not url:
            log(site,collection,'MISSING_ELEVATION_ASSET',list(it.assets.keys()));continue
        try:
            import planetary_computer as pc
            signed=pc.sign(url)
            a=warp_asset(signed,transform,shape,Resampling.bilinear)
            if np.isfinite(a).sum()<30:raise ValueError('Insufficient valid elevation coverage')
            save_tiff(ROOT/site/'rasters'/f'{collection}_elevation_m.tif',a,transform)
            slope=slope_deg(a);save_tiff(ROOT/site/'rasters'/f'{collection}_slope_deg.tif',slope,transform)
            slopes[collection]=slope
            for t in CFG['slope_thresholds_deg']:
                valid=np.isfinite(slope)
                stats.append(dict(site=site,model=collection,threshold_deg=t,valid_pixels=int(valid.sum()),
                    below=int(np.sum(valid&(slope<t))),above=int(np.sum(valid&(slope>=t))),
                    role='CROSS_MODEL_DESCRIPTIVE_NOT_GROUND_TRUTH'))
            log(site,collection,'RASTER_READY',f'{int(np.isfinite(slope).sum())} slope pixels')
        except Exception as e:log(site,collection,'RASTER_FAILED',repr(e))
    if stats:
        p=ROOT/site/'slope_counts.csv'
        with p.open('w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(stats[0]));wr.writeheader();wr.writerows(stats)
    disagreements=[]
    keys=sorted(slopes)
    for i,k1 in enumerate(keys):
        for k2 in keys[i+1:]:
            a,c=slopes[k1],slopes[k2];valid=np.isfinite(a)&np.isfinite(c)
            for t in CFG['slope_thresholds_deg']:
                disagreements.append(dict(site=site,a=k1,b=k2,threshold=t,common_pixels=int(valid.sum()),
                    disagreed=int(np.sum(valid&((a>=t)!=(c>=t)))),
                    disagreement_pct=float(100*np.mean((a[valid]>=t)!=(c[valid]>=t))) if valid.any() else None,
                    interpretation='DISAGREEMENT_NOT_ACCURACY'))
    if disagreements:
        p=ROOT/site/'pairwise_disagreement.csv'
        with p.open('w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(disagreements[0]));wr.writeheader();wr.writerows(disagreements)
    try:
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for k,a in slopes.items():
            fig,ax=plt.subplots(figsize=(7,6));im=ax.imshow(a,vmin=0,vmax=40,cmap='viridis');fig.colorbar(im,ax=ax,label='Slope, degrees')
            ax.set_title(f'{site} | {k} | DSM DEM-derived slope (not validation)');ax.axis('off')
            fig.savefig(ROOT/site/'figures'/f'{k}_slope.png',dpi=150,bbox_inches='tight');plt.close(fig)
    except Exception as e:log(site,'figures','PLOT_FAILED',str(e))
def opt_metadata(site,items,b):
    """Discover optical/SAR, and cautiously retrieve optical red/nir snippets."""
    lines=[]
    tr,shape=target_grid(b)
    for coll in ('sentinel-2-l2a','landsat-c2-l2','sentinel-1-grd'):
        for it in items.get(coll,[])[:CFG['max_scenes_per_collection']]:
            lines.append({'collection':coll,'id':it.id,'date':it.properties.get('datetime'),
                'cloud':it.properties.get('eo:cloud_cover'),'mode':'CATALOG_DISCOVERY',
                'warning':'Scene cloud percentage not equivalent to local cloud/snow masking'})
            if coll=='sentinel-1-grd':continue
            try:
                import planetary_computer as pc
                if coll=='sentinel-2-l2a':
                    redkey=next((k for k in ('B04','red') if k in it.assets),None)
                    nirkey=next((k for k in ('B08','nir') if k in it.assets),None)
                else:
                    redkey=next((k for k in ('red','SR_B4') if k in it.assets),None)
                    nirkey=next((k for k in ('nir08','SR_B5') if k in it.assets),None)
                if not redkey or not nirkey:raise ValueError('Red or NIR band missing')
                a=warp_asset(pc.sign(it.assets[redkey].href),tr,shape,Resampling.bilinear)
                c=warp_asset(pc.sign(it.assets[nirkey].href),tr,shape,Resampling.bilinear)
                if coll=='landsat-c2-l2':
                    a=a*0.0000275-0.2;c=c*0.0000275-0.2
                else:
                    # Sentinel-2 baseline-dependent quantification offsets need item-specific evaluation.
                    a=a/10000.0;c=c/10000.0
                with np.errstate(invalid='ignore',divide='ignore'):
                    ndvi=(c-a)/(c+a)
                ndvi=np.where((np.isfinite(ndvi))&(np.abs(c+a)>1e-4)&(ndvi>=-1)&(ndvi<=1),ndvi,np.nan)
                save_tiff(ROOT/site/'rasters'/f'{coll}_exploratory_ndvi.tif',ndvi,tr)
                log(site,coll,'EXPLORATORY_NDVI_READY',f'{int(np.isfinite(ndvi).sum())} unmasked pixels; no cloud/snow QA')
            except Exception as e:log(site,coll,'OPTICAL_RASTER_FAILED',repr(e))
    write(ROOT/site/'optical_and_sar_discovery.json',lines)
def cdse_check(site,b):
    try:
        r=requests.get(CFG['cdse_catalog']+'/collections/sentinel-2-l2a/items',params={'bbox':','.join(map(str,b)),'limit':3},timeout=25)
        r.raise_for_status();o=r.json()
        write(ROOT/site/'catalog'/'cdse_sentinel_2_crosscheck.json',[{'id':z.get('id'),'datetime':z.get('properties',{}).get('datetime')} for z in o.get('features',[])])
        log(site,'CDSE-S2','FOUND','independent catalog cross-check',len(o.get('features',[])))
    except Exception as e:log(site,'CDSE-S2','SEARCH_FAILED',str(e))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--site',default='all');args=parser.parse_args()
    try:
        from pystac_client import Client
        client=Client.open(CFG['stac_catalog'])
    except Exception as e:
        client=None;log('all','Planetary Computer','CATALOG_UNAVAILABLE',e)
    for site,p in CFG['sites'].items():
        if args.site!='all' and args.site!=site:continue
        b=bbox(p['lon'],p['lat'],p['radius_km']);write(ROOT/site/'region.json',{'site':site,'bbox_wgs84':b,'point':p,'AOI_is_provisional_square':True})
        its={k:search(client,k,b,site) if client else [] for k in CFG['collections']}
        cdse_check(site,b);opt_metadata(site,its,b);terrain(site,its,b)
    p=ROOT/'run_status.csv'
    with p.open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=['site','source','status','details','count']);wr.writeheader();wr.writerows(AUDIT)
    write(ROOT/'manifest.json',{'project':CFG['run_label'],'thresholds':CFG['slope_thresholds_deg'],
      'reference_DTM_available':False,'validation_AURC_run':False,'input_policy':'No restricted KazEOSat imagery distributed or fetched without legal access',
      'error_handling':'Per-source failures preserved in run_status.csv'})
    with (ROOT/'sha256.txt').open('w') as f:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and p.name!='sha256.txt':f.write(f'{sha(p)}  {p.relative_to(ROOT)}\n')
if __name__=='__main__':main()
