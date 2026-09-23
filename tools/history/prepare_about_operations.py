"""Offline public display data. Never writes to the private archive or operational DB.

--calendar reads LOCAL TIME from CSV rows in Log.zip. --routes uses local OSRM.
Only synthetic route numbers, coordinates and local seconds-of-day are published.
"""
import argparse
import csv
import io
import json
import math
import re
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import MultiPoint, Point, shape, mapping
from shapely.ops import transform
from prepare_legacy_regions import boundaries

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT/'backend/app/static/data/history/kaleh'
DEPOT = [51.554142,35.729941]
FWD = Transformer.from_crs(4326,32639,always_xy=True).transform
BACK = Transformer.from_crs(32639,4326,always_xy=True).transform
PALETTE = ['#2563eb','#0d9488','#7c3aed','#d97706','#0891b2','#e11d48','#4f46e5','#65a30d','#ea580c','#0284c7','#9333ea','#059669','#db2777','#475569','#ca8a04','#0f766e']


def write(name, value):
    path=PUBLIC/name; path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')


def collection(features): return {'type':'FeatureCollection','features':features}
def feature(g, **properties): return {'type':'Feature','geometry':mapping(g),'properties':properties}


def prepare_regions():
    official=[feature(transform(BACK,b.simplify(45,preserve_topology=True)),region=i)
              for i,b in sorted(boundaries().items())]
    write('municipal-regions.geojson',collection(official))
    tracks=json.loads((PUBLIC/'gps-tracks.geojson').read_text())['features']
    footprints=[]; operation=[]; transit=[]; stats=[]
    for f in tracks:
        p=f['properties']; route=p['route']; color=p['color']
        # Local density and dwell-time weighting excludes sparse highway transit.
        coords=np.array([xy for segment in f['geometry']['coordinates'] for xy in segment])
        xy=np.array([FWD(*v) for v in coords])
        dist=np.sqrt(((xy[:,None,:]-xy[None,:,:])**2).sum(axis=2))
        dwell=[]
        for segment,ts in zip(f['geometry']['coordinates'],p['times']):
            dwell.extend([min(180,max(1,ts[min(j+1,len(ts)-1)]-ts[j])) for j in range(len(ts))])
        weights=np.sqrt(np.array(dwell))
        density=(dist<1600)@weights
        center=int(np.argmax(density))
        nearby=np.flatnonzero(dist[center]<2400)
        # Buffer recorded points, not a hull of the entire cross-city journey.
        g=MultiPoint(xy[nearby]).convex_hull.buffer(250).simplify(40,preserve_topology=True)
        footprints.append(g)
        op_segments=[];op_times=[];transit_segments=[]
        for segment,ts in zip(f['geometry']['coordinates'],p['times']):
            run=[]; times=[]; access=[]
            for point,t in zip(segment,ts):
                if g.buffer(80).covers(Point(FWD(*point))):
                    run.append(point);times.append(t)
                    if len(access)>1:transit_segments.append(access)
                    access=[]
                else:
                    access.append(point)
                    if len(run)>1:op_segments.append(run);op_times.append(times)
                    run=[];times=[]
            if len(run)>1:op_segments.append(run);op_times.append(times)
            if len(access)>1:transit_segments.append(access)
        if not op_segments: raise ValueError(f'No recorded service segment for route {route}')
        operation.append({'type':'Feature','properties':{'route':route,'color':color,'times':op_times},'geometry':{'type':'MultiLineString','coordinates':op_segments}})
        if transit_segments:transit.append({'type':'Feature','properties':{'route':route,'color':color,'kind':'recorded_transit'},'geometry':{'type':'MultiLineString','coordinates':transit_segments}})
        stats.append((route,len(nearby),len(coords),round(g.area/1e6,3),[round(v,3) for v in transform(BACK,g).bounds]))
    # Keep all sixteen extents while assigning overlaps to the smaller footprint.
    assigned=None; geometries={}
    for i in sorted(range(16),key=lambda i:footprints[i].area):
        g=footprints[i] if assigned is None else footprints[i].difference(assigned.buffer(30))
        if g.is_empty:raise ValueError(f'Empty service area {i+1}')
        geometries[i]=g;assigned=g if assigned is None else assigned.union(g)
    summary=json.loads((PUBLIC/'smart-summary.json').read_text())
    features=[]
    for i in range(16):
        g=transform(BACK,geometries[i]); center=g.representative_point()
        features.append(feature(g,group=i+1,color=PALETTE[i],store_count=summary['groups'][i]['store_count'],label_center=[center.x,center.y]))
    write('smart-regions.geojson',collection(features))
    write('operation-tracks.geojson',collection(operation))
    write('transit-tracks.geojson',collection(transit))
    print('Service footprint diagnostics (route, dense points, total points, square km, bounds):',stats)


def parse_calendar():
    groups=defaultdict(dict); parsed=0; skipped=0; multifile=0
    number=re.compile(r'[-+]?\d+(?:\.\d+)?')
    with zipfile.ZipFile(ROOT/'data/history/kaleh/source/Log.zip') as archive:
        for entry in archive.infolist():
            parts=entry.filename.replace('\\','/').split('/')
            if not entry.filename.lower().endswith('.csv') or len(parts)<2 or not re.fullmatch(r'\d{2}',parts[-2]):continue
            dates=set()
            with archive.open(entry) as stream:
                for row in csv.DictReader(io.TextIOWrapper(stream,encoding='utf-8-sig',errors='replace')):
                    try:
                        dt=datetime.fromisoformat(row['LOCAL TIME'].replace('/','-'))
                        lon=float(number.search(row['LONGITUDE'])[0]);lat=float(number.search(row['LATITUDE'])[0])
                        if not (50.8<lon<51.85 and 35.35<lat<36.05):continue
                        date=dt.date().isoformat();second=dt.hour*3600+dt.minute*60+dt.second
                        dates.add(date);parsed+=1
                        groups[(date,parts[-2])][second]=(lon,lat)
                    except (ValueError,KeyError,TypeError):skipped+=1
            multifile+=len(dates)>1
    days=defaultdict(list)
    for (date,vehicle),rows in sorted(groups.items()):
        segments=[];times=[];run=[];ts=[];previous=None
        def finish():
            if len(run)>1:segments.append(run.copy());times.append(ts.copy())
        for t,point in sorted(rows.items()):
            if previous:
                dt=t-previous[0];d=math.hypot((point[0]-previous[1][0])*90500,(point[1]-previous[1][1])*111000)
                if dt<=0 or (dt<600 and d/dt>45):continue
                if dt>600:finish();run=[];ts=[]
                elif d<40 and dt<60:continue
            run.append([round(v,5) for v in point]);ts.append(t);previous=(t,point)
        finish()
        if segments:
            # Deterministic per-day pseudonym, never expose the archive vehicle name.
            n=len(days[date])+1
            days[date].append({'type':'Feature','properties':{'route':n,'color':PALETTE[(n-1)%16],'times':times},'geometry':{'type':'MultiLineString','coordinates':segments}})
    index=[]
    for date,features in sorted(days.items()):
        first=min(f['properties']['times'][0][0] for f in features)
        last=max(f['properties']['times'][-1][-1] for f in features)
        write(f'calendar/{date}.geojson',collection(features))
        index.append({'date':date,'vehicles':len(features),'start':first,'end':last,'file':date+'.geojson'})
    write('calendar/index.json',{'time_basis':'LOCAL TIME from each CSV row; seconds since local midnight','depot':DEPOT,'days':index})
    print('Calendar rows:',parsed,'invalid:',skipped,'files spanning multiple actual dates:',multifile)
    print('Days:',[(d['date'],d['vehicles']) for d in index])


def route(a,b):
    url=f'http://127.0.0.1:5000/route/v1/driving/{a[0]},{a[1]};{b[0]},{b[1]}?overview=full&geometries=geojson&steps=false'
    with urllib.request.urlopen(url,timeout=40) as response: value=json.load(response)
    if value.get('code')!='Ok':raise ValueError('OSRM route unavailable')
    r=value['routes'][0]; coordinates=r['geometry']['coordinates']
    # OSRM snaps endpoints to roads. Retain the exact public endpoints for seamless joins.
    coordinates[0]=a;coordinates[-1]=b
    return coordinates,r['duration'],r['distance']


def prepare_routes():
    tracks=json.loads((PUBLIC/'operation-tracks.geojson').read_text())['features'];features=[]
    for f in tracks:
        segments=f['geometry']['coordinates'];p=f['properties']
        coords,duration,distance=route(DEPOT,segments[0][0])
        features.append({'type':'Feature','properties':{'route':p['route'],'color':p['color'],'kind':'routed_access_not_recorded_gps','duration':duration,'distance':distance},'geometry':{'type':'LineString','coordinates':coords}})
        # Bridge missing recordings on roads; never interpolate straight across gaps.
        for a,b in zip(segments,segments[1:]):
            if a[-1]==b[0]:continue
            coords,duration,distance=route(a[-1],b[0])
            features.append({'type':'Feature','properties':{'route':p['route'],'color':p['color'],'kind':'routed_gap_not_recorded_gps','after_segment':segments.index(a),'duration':duration,'distance':distance},'geometry':{'type':'LineString','coordinates':coords}})
    write('access-routes.geojson',collection(features))
    print('Routed connections:',len(features),'depot starts:',sum(f['properties']['kind']=='routed_access_not_recorded_gps' for f in features))
    index=json.loads((PUBLIC/'calendar/index.json').read_text())
    for day in index['days']:
        day_tracks=json.loads((PUBLIC/'calendar'/day['file']).read_text())['features'];access=[]
        for f in day_tracks:
            coords,duration,distance=route(DEPOT,f['geometry']['coordinates'][0][0])
            access.append({'type':'Feature','properties':{'route':f['properties']['route'],'color':f['properties']['color'],'kind':'routed_access_not_recorded_gps','duration':duration,'distance':distance},'geometry':{'type':'LineString','coordinates':coords}})
        write('calendar/'+day['date']+'-access.geojson',collection(access))
    print('Calendar road access generated for',len(index['days']),'days using local OSRM')


def restore_full_gps():
    """Preserve every public GPS point and all approved depot-access features verbatim."""
    tracks=json.loads((PUBLIC/'gps-tracks.geojson').read_text())
    access=json.loads((PUBLIC/'access-routes.geojson').read_text())['features']
    bridges=[]
    for f in tracks['features']:
        p=f['properties'];segments=f['geometry']['coordinates']
        arrival=next(a for a in access if a['properties']['route']==p['route'] and a['properties']['kind']=='routed_access_not_recorded_gps')
        pairs=[(-1,arrival['geometry']['coordinates'][-1],segments[0][0])]
        pairs.extend((i,a[-1],b[0]) for i,(a,b) in enumerate(zip(segments,segments[1:])))
        for index,a,b in pairs:
            if a==b:continue
            coords,duration,distance=route(a,b)
            bridges.append({'type':'Feature','properties':{'route':p['route'],'color':p['color'],'kind':'routed_full_gps_connection','after_segment':index,'duration':duration,'distance':distance},'geometry':{'type':'LineString','coordinates':coords}})
    write('gps-continuity.geojson',collection(bridges))
    (PUBLIC/'operation-tracks.geojson').write_bytes((PUBLIC/'gps-tracks.geojson').read_bytes())
    print('GPS input/output:',[(f['properties']['route'],sum(map(len,f['geometry']['coordinates'])),len(f['geometry']['coordinates'])) for f in tracks['features']])


def prepare_operational_hulls():
    """Broad GPS operation extents; never derive service polygons from routed access.

    Preserve the original archive-derived public GPS unchanged. Route 11's two
    complete western recordings are its service operation; its eastern outbound
    and return recordings are transit. Route 15's repeated cross-city prefix and
    suffix are transit, bounded by the recorded entry/exit at longitude 51.35.
    No interior operational point or segment is filtered or simplified.
    """
    tracks=json.loads((PUBLIC/'gps-tracks.geojson').read_text())['features']
    summary=json.loads((PUBLIC/'smart-summary.json').read_text())
    stores={g['group']:g['store_count'] for g in summary['groups']}
    polygons=[];operations=[];arrivals=[];gaps=[];diagnostics=[]

    def road(points):
        coords=';'.join(f'{p[0]},{p[1]}' for p in points)
        url=f'http://127.0.0.1:5000/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=true&continue_straight=true'
        with urllib.request.urlopen(url,timeout=40) as response: value=json.load(response)
        if value.get('code')!='Ok': raise ValueError('Local OSRM route unavailable')
        r=value['routes'][0]; line=r['geometry']['coordinates']
        line[0]=points[0];line[-1]=points[-1]
        steps=[s for leg in r['legs'] for s in leg['steps']]
        return line,r['duration'],r['distance'],steps

    for f in tracks:
        p=f['properties'];n=p['route'];original=f['geometry']['coordinates'];times=p['times']
        if n==11:
            assert len(original)==4 and all(max(x[0] for x in original[i])<51.02 for i in (1,2))
            segments=[original[1],original[2]];selected_times=[times[1],times[2]]
        elif n==15:
            assert len(original)==1
            indices=[i for i,xy in enumerate(original[0]) if xy[0]<=51.35]
            a,b=min(indices),max(indices)
            segments=[original[0][a:b+1]];selected_times=[times[0][a:b+1]]
        else:
            segments=original;selected_times=times
        hull=MultiPoint([FWD(*xy) for segment in segments for xy in segment]).convex_hull
        if hull.area<=0: raise ValueError(f'Non-polygon GPS hull for route {n}')
        target=hull.area*1.1;lo=0.;hi=max(100.,math.sqrt(hull.area))
        for _ in range(55):
            mid=(lo+hi)/2
            if hull.buffer(mid).area<target:lo=mid
            else:hi=mid
        footprint=hull.buffer((lo+hi)/2)
        assert abs(footprint.area/hull.area-1.1)<1e-8 and footprint.covers(hull)
        geo=transform(BACK,footprint);center=geo.representative_point()
        polygons.append(feature(geo,group=n,color=p['color'],store_count=stores[n],label_center=[center.x,center.y]))
        operations.append({'type':'Feature','properties':dict(p,times=selected_times),'geometry':{'type':'MultiLineString','coordinates':segments}})
        # Southern Azadegan westbound carriageway: use a road-centre waypoint,
        # avoiding a detour to the parallel carriageway at coarse GPS precision.
        via=[[51.409828,35.614663],[51.321,35.627]] if n==11 else []
        line,duration,distance,steps=road([DEPOT,*via,segments[0][0]])
        edges=[tuple(sorted((tuple(a),tuple(b)))) for a,b in zip(line,line[1:]) if a!=b]
        assert len(edges)==len(set(edges)), f'Repeated access road edge: {n}'
        if n==11:
            names=' '.join(s.get('name','') for s in steps)
            assert '\u0647\u0645\u062a' not in names and 'hemmat' not in names.lower()
            assert '\u0622\u0632\u0627\u062f\u06af\u0627\u0646' in names or 'azadegan' in names.lower(), names
        arrivals.append({'type':'Feature','properties':{'route':n,'color':p['color'],'kind':'routed_access_not_recorded_gps','duration':duration,'distance':distance},'geometry':{'type':'LineString','coordinates':line}})
        for index,(a,b) in enumerate(zip(segments,segments[1:])):
            if a[-1]==b[0]:continue
            line,duration,distance,_=road([a[-1],b[0]])
            gaps.append({'type':'Feature','properties':{'route':n,'color':p['color'],'kind':'routed_full_gps_connection','after_segment':index,'duration':duration,'distance':distance},'geometry':{'type':'LineString','coordinates':line}})
        diagnostics.append({'route':n,'input_points':sum(map(len,original)),'operation_points':sum(map(len,segments)),
                            'operation_segments':len(segments),'hull_km2':round(hull.area/1e6,3),
                            'polygon_km2':round(footprint.area/1e6,3),'buffer_m':round((lo+hi)/2,2),
                            'access_uturns':sum(s.get('maneuver',{}).get('modifier')=='uturn' for s in steps)})
    assert len(polygons)==len(operations)==len(arrivals)==16
    # Publish only once every route, containment and area assertion succeeds.
    write('smart-regions.geojson',collection(polygons))
    write('operation-tracks.geojson',collection(operations))
    write('access-routes.geojson',collection(arrivals))
    write('gps-continuity.geojson',collection(gaps))
    print(json.dumps(diagnostics,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--calendar',action='store_true');parser.add_argument('--regions',action='store_true');parser.add_argument('--routes',action='store_true');parser.add_argument('--restore-full-gps',action='store_true');parser.add_argument('--operational-hulls',action='store_true');args=parser.parse_args()
    if args.regions:prepare_regions()
    if args.calendar:parse_calendar()
    if args.routes:prepare_routes()
    if args.restore_full_gps:restore_full_gps()
    if args.operational_hulls:prepare_operational_hulls()
