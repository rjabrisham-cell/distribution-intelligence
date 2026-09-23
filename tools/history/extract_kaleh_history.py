"""Read-only local Access/ZIP extraction. Never import history into DIP's database."""
from pathlib import Path
import base64
import json
import subprocess
import csv
import io
import math
import re
import zipfile
from datetime import datetime

import numpy as np
from pyproj import Transformer
from shapely.geometry import MultiPoint, mapping

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/history/kaleh/source'
PRIVATE = ROOT / 'data/history/kaleh/generated'
PUBLIC = ROOT / 'backend/app/static/data/history/kaleh'


def read_access(queries):
    """Windows ACE provider; only caller-selected, non-personal columns are read."""
    script = r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$queries = ConvertFrom-Json ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('QUERIES')))
$c=New-Object System.Data.OleDb.OleDbConnection('Provider=Microsoft.ACE.OLEDB.12.0;Data Source=MDBPATH;Mode=Read;')
$c.Open()
try {
 $out=@{}
 foreach($q in $queries.PSObject.Properties) {
  $cmd=$c.CreateCommand(); $cmd.CommandText=$q.Value; $r=$cmd.ExecuteReader()
  $rows=New-Object System.Collections.Generic.List[object]
  while($r.Read()) { $row=@{}; for($i=0;$i -lt $r.FieldCount;$i++) { $v=$r.GetValue($i); if($v -is [DBNull]) {$v=$null}; $row[$r.GetName($i)]=$v }; $rows.Add($row) }
  $r.Close(); $out[$q.Name]=$rows.ToArray()
 }
 ConvertTo-Json -InputObject $out -Depth 8 -Compress
} finally { $c.Close() }
'''.replace('QUERIES', base64.b64encode(json.dumps(queries).encode()).decode()).replace('MDBPATH', str(SOURCE / 'Tourism.mdb').replace("'", "''"))
    encoded = base64.b64encode(script.encode('utf-16-le')).decode()
    process = subprocess.run(['powershell', '-NoProfile', '-EncodedCommand', encoded],
                             capture_output=True)
    if process.returncode:
        raise RuntimeError('Read-only Access query failed; verify the ACE provider and input schema')
    return json.loads(process.stdout.decode('utf-8-sig'))


def assignment(cost):
    """Rectangular minimum-cost, one-to-one assignment; no external optimizer."""
    n, m = cost.shape
    if m < n:
        raise ValueError('Not enough usable GPS groups')
    u, v, p, way = [0.]*(n+1), [0.]*(m+1), [0]*(m+1), [0]*(m+1)
    for i in range(1, n+1):
        p[0] = i
        j0 = 0
        minimum, used = [float('inf')]*(m+1), [False]*(m+1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], float('inf'), 0
            for j in range(1, m+1):
                if not used[j]:
                    cur = cost[i0-1, j-1]-u[i0]-v[j]
                    if cur < minimum[j]: minimum[j], way[j] = cur, j0
                    if minimum[j] < delta: delta, j1 = minimum[j], j
            for j in range(m+1):
                if used[j]: u[p[j]] += delta; v[j] -= delta
                else: minimum[j] -= delta
            j0 = j1
            if p[j0] == 0: break
        while j0:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
    result = [None]*n
    for j in range(1,m+1):
        if p[j]: result[p[j]-1] = j-1
    return result


def simplify(points, epsilon=70):
    """RDP in approximate metres, retaining timestamps and stationary durations."""
    xy = points[:, :2] * np.array([90500, 111000])
    keep = {0, len(points)-1}
    # Preserve significant stops, with both arrival and departure times.
    start = 0
    rounded = np.round(points[:, :2], 3)
    for i in range(1, len(points)+1):
        if i == len(points) or np.any(rounded[i] != rounded[start]):
            if points[i-1, 2]-points[start, 2] >= 90: keep.update([start, i-1])
            start = i
    stack = [(0,len(points)-1)]
    while stack:
        a,b = stack.pop()
        if b-a<2: continue
        line = xy[b]-xy[a]
        length = float(line @ line)
        distance = np.linalg.norm(xy[a+1:b]-xy[a],axis=1) if not length else np.linalg.norm(
            xy[a+1:b]-(xy[a]+np.clip(((xy[a+1:b]-xy[a])@line)/length,0,1)[:,None]*line),axis=1)
        k = int(np.argmax(distance))+a+1
        if distance[k-a-1]>epsilon:
            keep.add(k); stack.extend([(a,k),(k,b)])
    return points[sorted(keep)]


def gps_candidates():
    cache=PRIVATE/'gps-candidates.npz'
    stamp=str((SOURCE/'Log.zip').stat().st_mtime_ns)
    if cache.exists():
        with np.load(cache,allow_pickle=False) as stored:
            if str(stored['stamp'])==stamp:
                metadata=json.loads(str(stored['metadata']))
                return [dict(item,points=stored['p'+str(i)]) for i,item in enumerate(metadata)]
    candidates = []
    with zipfile.ZipFile(SOURCE/'Log.zip') as archive:
        for entry in archive.infolist():
            parts = entry.filename.replace('\\','/').split('/')
            if not entry.filename.lower().endswith('.csv') or len(parts)<2 or not re.fullmatch(r'\d{2}',parts[-2]):
                continue
            rows=[]
            with archive.open(entry) as stream:
                for row in csv.DictReader(io.TextIOWrapper(stream,encoding='utf-8-sig',errors='replace')):
                    try:
                        lat=float(re.search(r'[-+]?\d+(?:\.\d+)?',row['LATITUDE'])[0])
                        lon=float(re.search(r'[-+]?\d+(?:\.\d+)?',row['LONGITUDE'])[0])
                        timestamp=datetime.strptime(row['UTC'],'%Y/%m/%d %H:%M:%S.%f').timestamp()
                        if 35.35<lat<36.05 and 50.8<lon<51.85: rows.append((lon,lat,timestamp))
                    except (ValueError,KeyError,TypeError): continue
            rows=sorted(set(rows),key=lambda p:p[2])
            clean=[]
            for row in rows:
                if clean:
                    dt=row[2]-clean[-1][2]
                    distance=math.hypot((row[0]-clean[-1][0])*90500,(row[1]-clean[-1][1])*111000)
                    if dt<=0 or distance/dt>36: continue
                clean.append(row)
            if len(clean)<30 or clean[-1][2]-clean[0][2]<600: continue
            points=np.array(clean)
            candidates.append({'vehicle':int(parts[-2]),'points':points,'source':entry.filename})
    metadata=[{k:v for k,v in c.items() if k!='points'} for c in candidates]
    np.savez_compressed(cache,stamp=stamp,metadata=json.dumps(metadata),
                        **{'p'+str(i):c['points'] for i,c in enumerate(candidates)})
    return candidates


def feature(geometry, **properties):
    return {'type':'Feature','geometry':geometry,'properties':properties}


def collection(features):
    return {'type':'FeatureCollection','features':features}


def main():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    raw=read_access({
        'customers':'SELECT Code,PointX,PointY FROM DistributionCustomer',
        'groups':'SELECT ID,Code,BlockOrder FROM DistributionTemp',
        'orders':'SELECT Code,Weight FROM DistributionCOrder',
        'regions':'SELECT LocalId FROM DistributionLocal',
    })
    # No names, telephone numbers, addresses, or driver records are selected.
    project=Transformer.from_crs(32639,4326,always_xy=True)
    coords={}
    for row in raw['customers']:
        x,y=row['PointX'],row['PointY']
        if x is None or y is None: continue
        lon,lat=project.transform(x,y)
        if 50.8<lon<51.85 and 35.35<lat<36.05: coords[str(row['Code'])]=(lon,lat)
    weights={str(r['Code']):float(r['Weight'] or 0) for r in raw['orders']}
    groups={i:[] for i in range(16)}
    loads={i:0 for i in range(16)}
    counts={i:0 for i in range(16)}
    for row in raw['groups']:
        i=int(row['ID']); code=str(row['Code'])
        if i not in groups: raise ValueError('Unexpected planning group')
        counts[i]+=1; loads[i]+=weights.get(code,0)
        if code in coords: groups[i].append(coords[code])
    if any(len(v)<3 for v in groups.values()): raise ValueError('Planning group lacks defensible coordinates')
    candidates=gps_candidates()
    vehicles=sorted({c['vehicle'] for c in candidates})
    costs=np.full((16,len(vehicles)),1e6)
    best={}
    for ci,c in enumerate(candidates):
        pts=c['points'][::max(1,len(c['points'])//500)]
        movement=np.linalg.norm(np.diff(c['points'][:,:2],axis=0)*[90500,111000],axis=1)
        dt=np.diff(c['points'][:,2])
        stops=c['points'][1:][movement/np.maximum(dt,1)<.8][::20]
        vi=vehicles.index(c['vehicle'])
        for i, stores in groups.items():
            xy=np.array(stores)
            distances=np.linalg.norm((pts[:,None,:2]-xy[None,:,:])*[90500,111000],axis=2)
            coverage=float(np.mean(np.min(distances,axis=0)<600))
            overlap=float(np.mean(np.min(distances,axis=1)<900))
            stop_overlap=0.
            if len(stops):
                sd=np.linalg.norm((stops[:,None,:2]-xy[None,:,:])*[90500,111000],axis=2)
                stop_overlap=float(np.mean(np.min(sd,axis=1)<600))
            score=.5*coverage+.3*overlap+.2*stop_overlap
            if 1-score<costs[i,vi]:
                costs[i,vi]=1-score;best[i,vi]=(ci,coverage,overlap,stop_overlap)
    chosen=assignment(costs)
    planned=[];tracks=[];report=[]
    total_load=sum(loads.values())
    palette=['#2563eb','#0d9488','#7c3aed','#d97706','#0891b2','#db2777','#4f46e5','#65a30d','#c2410c','#0284c7','#9333ea','#059669','#be123c','#475569','#a16207','#0f766e']
    for i,vi in enumerate(chosen):
        ci,coverage,overlap,stop_overlap=best[i,vi];candidate=candidates[ci]
        hull=MultiPoint(np.round(groups[i],3)).convex_hull
        if hull.geom_type!='Polygon': hull=hull.buffer(.001)
        geometry=json.loads(json.dumps(mapping(hull)))
        geometry['coordinates']=[[[round(x,3),round(y,3)] for x,y in ring] for ring in geometry['coordinates']]
        planned.append(feature(geometry,route=i+1,color=palette[i],store_count=counts[i],
                               load_share=round(100*loads[i]/total_load,1),center=[round(hull.centroid.x,3),round(hull.centroid.y,3)]))
        points=candidate['points']
        # Keep only the operational vicinity; omit remote departures and endpoints.
        bounds=hull.buffer(.025).bounds
        mask=(points[:,0]>=bounds[0])&(points[:,0]<=bounds[2])&(points[:,1]>=bounds[1])&(points[:,1]<=bounds[3])
        segments=[];times=[];segment=[]
        origin=points[0,2]
        def finish():
            if len(segment)<2: return
            reduced=simplify(np.array(segment))
            segments.append([[round(p[0],3),round(p[1],3)] for p in reduced])
            times.append([round(p[2]-origin) for p in reduced])
        for row,inside in zip(points,mask):
            if not inside or (segment and row[2]-segment[-1][2]>300):
                finish();segment=[]
            if inside: segment.append(row)
        finish()
        if not segments:
            # Weak association: retain a real central recording segment, never
            # invent a road trace. Its geographic confidence remains private.
            segment=[]
            for row in points[len(points)//10:len(points)*9//10]:
                if segment and row[2]-segment[-1][2]>300:
                    finish();segment=[]
                segment.append(row)
            finish()
        offset=times[0][0];times=[[t-offset for t in ts] for ts in times]
        tracks.append(feature({'type':'MultiLineString','coordinates':segments},route=i+1,color=palette[i],times=times))
        report.append({'route':i+1,'source_vehicle':candidate['vehicle'],'source_file':candidate['source'],
                       'coverage':coverage,'overlap':overlap,'stops':stop_overlap,'confidence_score':round(1-costs[i,vi],3)})
    summary={'schema_version':1,'chapter':'kaleh-tehran','customer_archive_count':len(raw['customers']),
             'legacy_region_count':len(raw['regions']),'initial_trucks':21,'route_count':16,
             'planned_record_count':len(raw['groups']),'coordinate_record_count':sum(map(len,groups.values())),
             'gps_point_count':sum(sum(map(len,f['geometry']['coordinates'])) for f in tracks),
             'duration_seconds':max(max(ts[-1] for ts in f['properties']['times']) for f in tracks),
             'legacy_geometry':'schematic','planned_geometry':'customer_extent_not_road_route',
             'playback':'relative_time_separate_recordings','coordinate_precision_decimals':3,
             'initial_trucks_source':'project_owner_historical_account',
             'datasets':{'legacy':'legacy-regions.geojson','planned':'planned-routes.geojson','gps':'gps-tracks.geojson'}}
    legacy=[feature(None,region=i,truck=min(i,21)) for i in range(1,23)]
    PUBLIC.mkdir(parents=True,exist_ok=True)
    for name,data in [('history-summary.json',summary),('legacy-regions.geojson',collection(legacy)),
                      ('planned-routes.geojson',collection(planned)),('gps-tracks.geojson',collection(tracks))]:
        (PUBLIC/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    internal={'selected_routes':report,'projection_assumption':'WGS84 UTM 39N; checked against Tehran GPS bounds',
              'limitations':['Legacy boundary geometry absent: schematic only','No stored road paths or usable visit order; extents only',
                             'GPS replay uses relative times; not evidence of a single shared day',
                             'Load units unspecified; only shares published','Initial fleet count supplied by project owner, not derived from MDB']}
    (PRIVATE/'extraction-report.json').write_text(json.dumps(internal,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ['route_count','planned_record_count','coordinate_record_count','gps_point_count']},ensure_ascii=True))
    print('Public bytes:',sum(p.stat().st_size for p in PUBLIC.iterdir() if p.suffix in ['.json','.geojson']))


if __name__=='__main__': main()
