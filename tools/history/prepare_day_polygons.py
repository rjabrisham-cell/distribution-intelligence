"""Prepared public GPS only: sample 13 demo roads and selected calendar envelopes."""
import json
import math
import urllib.request
from bisect import bisect_left
from copy import deepcopy

from shapely.geometry import MultiPoint, Point, LineString, shape
from shapely.ops import transform
from prepare_about_operations import PUBLIC, DEPOT, FWD, BACK, collection, feature, write

DATES = ('2010-04-21', '2010-04-22', '2010-04-24', '2010-04-25')


def envelope(segments, **properties):
    hull = MultiPoint([FWD(*xy) for segment in segments for xy in segment]).convex_hull
    if hull.area <= 0:
        raise ValueError('Areal GPS envelope unavailable; no invented polygon fallback')
    low, high = 0., max(100., math.sqrt(hull.area))
    for _ in range(55):
        distance = (low + high) / 2
        if hull.buffer(distance).area < hull.area * 1.1:
            low = distance
        else:
            high = distance
    buffered = hull.buffer((low + high) / 2)
    assert buffered.covers(hull) and abs(buffered.area / hull.area - 1.1) < 1e-8
    polygon = transform(BACK, buffered)
    center = polygon.representative_point()
    return feature(polygon, **properties, label_center=[center.x, center.y])


def road(points, optimize=False, bearings=None):
    coordinates = ';'.join(f'{lon},{lat}' for lon, lat in points)
    service = 'trip' if optimize else 'route'
    options = '&roundtrip=false&source=first&destination=last' if optimize else '&continue_straight=true'
    if bearings: options += '&bearings='+bearings
    url = f'http://127.0.0.1:5000/{service}/v1/driving/{coordinates}?overview=full&geometries=geojson&steps=true'+options
    with urllib.request.urlopen(url, timeout=40) as response:
        value = json.load(response)
    if value.get('code') != 'Ok':
        raise ValueError('Existing local routing engine unavailable')
    result = value['trips' if optimize else 'routes'][0]
    coords = result['geometry']['coordinates']
    coords[0], coords[-1] = points[0], points[-1]
    return coords, result['duration'], result['distance']


def sample_thirteen():
    gps = json.loads((PUBLIC / 'gps-tracks.geojson').read_text())
    original = next(f for f in gps['features'] if f['properties']['route'] == 13)
    entry = original['geometry']['coordinates'][0][0]
    # A reproducible demonstration circuit through actual streets in districts 5/22.
    # This is explicitly synthetic, never presented as another archived GPS track.
    stops = [entry, [51.292,35.762], [51.295,35.773], [51.282,35.778],
             [51.274,35.774], [51.276,35.766], [51.265,35.766],
             [51.258,35.763], [51.247,35.761], [51.237,35.752],
             [51.226,35.757], [51.229,35.747], [51.242,35.746],
             [51.251,35.748], [51.259,35.753]]
    coords, duration, distance = road(stops, optimize=True)
    official = {f['properties']['region']:shape(f['geometry']) for f in
                json.loads((PUBLIC / 'municipal-regions.geojson').read_text())['features']}
    for region in (5,22):
        assert sum(official[region].covers(Point(xy)) for xy in coords) > 20
    times = [0.]
    for a,b in zip(coords, coords[1:]):
        ax,ay=FWD(*a); bx,by=FWD(*b)
        times.append(times[-1]+math.hypot(bx-ax,by-ay)/5.)
    operation = json.loads((PUBLIC / 'operation-tracks.geojson').read_text())
    polygons = json.loads((PUBLIC / 'smart-regions.geojson').read_text())
    access = json.loads((PUBLIC / 'access-routes.geojson').read_text())
    index = next(i for i,f in enumerate(operation['features']) if f['properties']['route']==13)
    color = operation['features'][index]['properties']['color']
    operation['features'][index] = {'type':'Feature', 'properties':{
        'route':13, 'color':color, 'times':[times], 'source':'synthetic_demo'},
        'geometry':{'type':'MultiLineString','coordinates':[coords]}}
    index = next(i for i,f in enumerate(polygons['features']) if f['properties']['group']==13)
    count = polygons['features'][index]['properties']['store_count']
    polygons['features'][index] = envelope([coords], group=13, color=color,
                                          store_count=count, source='synthetic_demo')
    # Reclassify the old east-west trace as the arrival corridor. Travel westwards
    # on the road network to its western entry, then join the demo operation.
    old = original['geometry']['coordinates'][0]
    arrival, seconds, metres = road([DEPOT, old[-1], entry], bearings=';270,45;')
    edges=[tuple(sorted((tuple(a),tuple(b)))) for a,b in zip(arrival,arrival[1:]) if a!=b]
    assert len(edges)==len(set(edges))
    index = next(i for i,f in enumerate(access['features']) if f['properties']['route']==13)
    access['features'][index] = {'type':'Feature', 'properties':{
        'route':13,'color':color,'kind':'routed_access_not_recorded_gps',
        'source':'routed_from_recorded_access_corridor','duration':seconds,'distance':metres},
        'geometry':{'type':'LineString','coordinates':arrival}}
    assert arrival[-1] == coords[0]
    write('operation-tracks.geojson', operation)
    write('smart-regions.geojson', polygons)
    write('access-routes.geojson', access)
    print('Sample 13: synthetic road vertices', len(coords), 'road km', round(distance/1000,2))


def classify_prefix(track):
    """Earliest sustained stop; afterwards every point/segment is operational.

    At least four samples, >=180 seconds, <=75m from the first sample, and no
    sampling gap over 90 seconds. Do not identify a depot-yard stop as delivery.
    Ambiguous/sparse timing retains the whole log, never a guessed late window.
    """
    segments=track['geometry']['coordinates']; times=track['properties'].get('times',[])
    first=(0,0);stop=None;reason='no_reliable_stop_keep_full_log'
    valid=len(times)==len(segments) and all(len(s)==len(t) and t==sorted(t) for s,t in zip(segments,times))
    valid=valid and all(a[-1]<=b[0] for a,b in zip(times,times[1:]))
    if valid:
        depot=FWD(*DEPOT)
        for segment_index,(coords,ts) in enumerate(zip(segments,times)):
            xy=[FWD(*p) for p in coords]
            for start in range(len(coords)):
                end=bisect_left(ts,ts[start]+180,lo=start)
                if end>=len(coords):break
                if end-start<3 or ts[end]-ts[start]>270:continue
                if max(b-a for a,b in zip(ts[start:end],ts[start+1:end+1]))>90:continue
                if math.dist(xy[start],depot)<750:continue
                if max(math.dist(xy[start],p) for p in xy[start:end+1])>75:continue
                first=(segment_index,start);reason='first_sustained_stop'
                stop={'segment':segment_index,'point':start,'time_seconds':ts[start],
                      'duration_seconds':ts[end]-ts[start],'samples':end-start+1}
                break
            if stop is not None:break
    else:reason='insufficient_timing_keep_full_log'
    segment_index,start=first
    spans=[[i,start if i==segment_index else 0,len(s)-1]
           for i,s in enumerate(segments) if i>=segment_index]
    prefix_count=sum(len(s) for s in segments[:segment_index])+start
    return spans,stop,prefix_count,reason


def operation_spans(track):
    return classify_prefix(track)[0]


def classify_window(track):
    """Hull-only window; all rendered GPS and animation retain the complete trip."""
    display_spans,first,prefix,reason=classify_prefix(track)
    segments=track['geometry']['coordinates']; times=track['properties']['times']
    offsets=[];total=0
    for segment in segments:offsets.append(total);total+=len(segment)
    all_xy=[FWD(*xy) for segment in segments for xy in segment]
    all_times=[t for ts in times for t in ts];depot=FWD(*DEPOT)
    distances=[math.dist(xy,depot) for xy in all_xy]
    last=None;end=total-1;return_reason='no_valid_stop_keep_end'
    if first:
        for si,(segment,ts) in enumerate(zip(segments,times)):
            xy=all_xy[offsets[si]:offsets[si]+len(segment)]
            for a in range(len(segment)):
                b=bisect_left(ts,ts[a]+180,lo=a)
                if b>=len(segment):break
                if offsets[si]+a<prefix or b-a<3 or ts[b]-ts[a]>270:continue
                if max(y-x for x,y in zip(ts[a:b],ts[a+1:b+1]))>90:continue
                if distances[offsets[si]+a]<750:continue
                if max(math.dist(xy[a],point) for point in xy[a:b+1])>75:continue
                last={'segment':si,'point':a,'end_point':b,'time_seconds':ts[a],
                      'end_time_seconds':ts[b],'duration_seconds':ts[b]-ts[a],
                      'record_1based':offsets[si]+a+1,'end_record_1based':offsets[si]+b+1}
        if distances[-1]>750:return_reason='end_not_near_depot_keep_end'
        elif last:
            candidate=last['end_record_1based']-1
            tail=distances[candidate:];best=tail[0];backtrack=0.
            for distance in tail:
                best=min(best,distance);backtrack=max(backtrack,distance-best)
            gaps=[b-a for a,b in zip(all_times[candidate:],all_times[candidate+1:])]
            # Tolerate road curvature/GPS jitter, but not an outbound detour or
            # an unobserved gap that could conceal another delivery stop.
            allowance=max(300.,tail[0]*.15)
            continuous=not gaps or max(gaps)<=180
            if candidate>prefix and tail[0]>750 and backtrack<=allowance and continuous:
                end=candidate;return_reason='continuous_return_after_last_valid_stop'
            else:return_reason='ambiguous_return_keep_end'
    spans=[]
    for si,segment in enumerate(segments):
        a=max(0,prefix-offsets[si]);b=min(len(segment)-1,end-offsets[si])
        if a<=b:spans.append([si,a,b])
    # Never create degenerate output to force a later cutoff.
    window_xy=all_xy[prefix:end+1]
    if MultiPoint(window_xy).convex_hull.area<=0 or any(a==b for _,a,b in spans):
        spans=display_spans;end=total-1;return_reason='ambiguous_geometry_keep_end'
    return display_spans,spans,first,last,prefix,total-end-1,reason,return_reason,distances[-1]


def calendar_polygons():
    index=json.loads((PUBLIC/'calendar/index.json').read_text())
    reports=[];outputs=[]
    for date in DATES:
        day=next(d for d in index['days'] if d['date']==date)
        counts={g['group']:g['store_count'] for g in day['display']['groups']}
        tracks=json.loads((PUBLIC/'calendar'/day['file']).read_text())['features']
        polygons=[];classified=[]
        access=json.loads((PUBLIC/'calendar'/f'{date}-access.geojson').read_text())['features']
        for f in access:
            f=deepcopy(f);f['properties'].update(type='access_route',source='computed_road_network');classified.append(f)
        for track in tracks:
            p=track['properties']
            display_spans,spans,stop,last_stop,prefix_count,return_count,reason,return_reason,end_distance=classify_window(track)
            segments=[track['geometry']['coordinates'][s][a:b+1] for s,a,b in spans]
            polygon=envelope(segments, group=p['route'], color=p['color'],
                store_count=counts[p['route']], source='recorded_gps_operation_envelope', operation_spans=spans)
            polygons.append(polygon)
            # Keep line rendering byte-equivalent to the previous complete suffix;
            # only the hull window changes, never the return route/animation.
            operation=deepcopy(track);operation['geometry']['coordinates']=[track['geometry']['coordinates'][s][a:b+1] for s,a,b in display_spans]
            operation['properties'].update(type='operational_gps',source='recorded_gps',
                times=[p['times'][s][a:b+1] for s,a,b in display_spans])
            classified.append(operation)
            first_segment,first_point,_=spans[0]
            # Include the shared entry vertex only for rendering the final prefix
            # edge. prefix_count counts strictly earlier records, not this vertex.
            prefix_segments=deepcopy(track['geometry']['coordinates'][:first_segment])
            prefix_times=deepcopy(p['times'][:first_segment])
            if first_point:
                prefix_segments.append(track['geometry']['coordinates'][first_segment][:first_point+1])
                prefix_times.append(p['times'][first_segment][:first_point+1])
            if prefix_segments:
                prefix=deepcopy(track);prefix['geometry']['coordinates']=prefix_segments
                prefix['properties'].update(type='access_route',source='recorded_gps_prefix',times=prefix_times)
                classified.append(prefix)
            xy=[[FWD(*point) for point in s] for s in segments]
            all_points=[point for s in xy for point in s]
            hull=MultiPoint(all_points).convex_hull
            geometry=transform(FWD,shape(polygon['geometry']))
            tolerance=geometry.buffer(.00001)  # 0.01 mm; numerical round-trip only.
            outside=sum(not tolerance.covers(Point(point)) for point in all_points)
            outside_lines=sum(not tolerance.covers(LineString(s)) for s in xy if len(s)>1)
            total=sum(map(len,track['geometry']['coordinates']))
            assert prefix_count+len(all_points)+return_count==total
            assert outside==outside_lines==0 and abs(geometry.area/hull.area-1.1)<1e-6
            reports.append({'date':date,'route':p['route'],'raw_points':total,
                'raw_segments':len(track['geometry']['coordinates']),
                'first_stop_record_1based':prefix_count+1 if stop else None,'stop':stop,
                'last_stop':last_stop,'return_suffix_points':return_count,
                'end_distance_to_depot_m':round(end_distance,2),'return_classification':return_reason,
                'classification':reason,'access_prefix_points':prefix_count,
                'operational_points':len(all_points),'operational_segments':len(segments),
                'hull_input_points':len(all_points),'outside_points':outside,'outside_segments':outside_lines,
                'area_ratio':round(geometry.area/hull.area,9),'operation_spans':spans})
        assert len(polygons)==day['vehicles']
        outputs.extend([(f'calendar/{date}-regions.geojson',collection(polygons)),
                        (f'calendar/{date}-operations.geojson',collection(classified))])
        print(date, 'polygons',len(polygons))
    for name,value in outputs:write(name,value)
    private=PUBLIC.parents[5]/'data/history/kaleh/generated'
    private.mkdir(parents=True,exist_ok=True)
    report={'input':'complete prepared daily GPS, in recorded chronological order',
            'stop_rule':'at least 4 samples, 180 seconds, radius 75m, max gap 90s, outside depot 750m',
            'sample_day_changed':False,'rows':reports}
    (private/'calendar-geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lines=['# Calendar geometry audit','',
           'Input is the complete prepared daily GPS; sample day and original GPS/access files unchanged.',
           'Record numbers are 1-based; times are local seconds after midnight. Null stop means full log retained.','',
           '|Day|Route|Raw points/segments|First stop record/time/duration|Last stop record/time/duration|Prefix|Operation points/segments|Return|End distance (m)|Hull points|Outside points/lines|Area ratio|Return decision|',
           '|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in reports:
        s=r['stop'];stop_text=f"{r['first_stop_record_1based']}/{s['time_seconds']}/{s['duration_seconds']}s" if s else 'none / full log'
        last=r['last_stop'];last_text=f"{last['record_1based']}/{last['time_seconds']}/{last['duration_seconds']}s" if last else 'none'
        lines.append(f"|{r['date']}|{r['route']}|{r['raw_points']}/{r['raw_segments']}|{stop_text}|{last_text}|{r['access_prefix_points']}|{r['operational_points']}/{r['operational_segments']}|{r['return_suffix_points']}|{r['end_distance_to_depot_m']}|{r['hull_input_points']}|{r['outside_points']}/{r['outside_segments']}|{r['area_ratio']}|{r['return_classification']}|")
    (private/'calendar-geometry-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Validated',len(reports),'vehicles; outside points/segments = 0; report:',private/'calendar-geometry-audit.md')


def targeted_hull_overrides():
    """Reviewed stop windows, 1-based records of the complete prepared GPS.

    Only polygon input changes. Recorded lines, timestamps and access stay intact.
    Earlier western stops are retained even when the main cluster starts later.
    """
    overrides=[('2010-04-25',8,993,1998,997,1995),
               ('2010-04-22',11,919,2477,922,2474),
               ('2010-04-21',5,942,2267,946,2264),
               ('2010-04-21',9,1175,2284,1179,2281)]
    report=[]
    for date,route,start,end,first_end,last_start in overrides:
        path=PUBLIC/'calendar'/f'{date}-regions.geojson'
        data=json.loads(path.read_text())
        track=next(f for f in json.loads((PUBLIC/'calendar'/f'{date}.geojson').read_text())['features'] if f['properties']['route']==route)
        coords=track['geometry']['coordinates'];times=track['properties']['times']
        flat=[p for s in coords for p in s];ts=[t for s in times for t in s]
        # Check actual stationary samples at each boundary, not a spatial clip.
        for a,b in [(start,first_end),(last_start,end)]:
            assert b-a>=3 and ts[b-1]-ts[a-1]>=180
            stop_xy=[FWD(*p) for p in flat[a-1:b]]
            assert max(math.dist(stop_xy[0],p) for p in stop_xy)<=75
        spans=[];offset=0
        for si,segment in enumerate(coords):
            a=max(0,start-1-offset);b=min(len(segment)-1,end-1-offset)
            if a<=b:spans.append([si,a,b])
            offset+=len(segment)
        parts=[coords[s][a:b+1] for s,a,b in spans]
        old=next(f for f in data['features'] if f['properties']['group']==route)
        properties=deepcopy(old['properties']);properties.pop('label_center',None)
        properties.update(operation_spans=spans,hull_override={'hull_start':start,'hull_end':end,
            'record_index_base':1,'start_time':ts[start-1],'end_time':ts[end-1],
            'reason':'reviewed first/last western distribution stop clusters; hull only'})
        new=envelope(parts,**properties)
        hull=MultiPoint([FWD(*p) for p in flat[start-1:end]]).convex_hull
        geometry=transform(FWD,shape(new['geometry']))
        outside=sum(not geometry.buffer(.00001).covers(Point(FWD(*p))) for p in flat[start-1:end])
        ratio=geometry.area/hull.area
        assert outside==0 and abs(ratio-1.1)<1e-6
        data['features'][data['features'].index(old)]=new
        write(f'calendar/{date}-regions.geojson',data)
        report.append({'date':date,'route':route,'hull_start':start,'hull_end':end,
            'start_time_seconds':ts[start-1],'end_time_seconds':ts[end-1],
            'first_stop_duration_seconds':ts[first_end-1]-ts[start-1],
            'last_stop_duration_seconds':ts[end-1]-ts[last_start-1],
            'full_trip_points':len(flat),'hull_points':end-start+1,'outside_points':outside,
            'area_ratio':round(ratio,9),'previous_area_km2':transform(FWD,shape(old['geometry'])).area/1e6,
            'area_km2':geometry.area/1e6})
    private=PUBLIC.parents[5]/'data/history/kaleh/generated'
    (private/'targeted-hull-overrides.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--include-sample-thirteen',action='store_true')
    parser.add_argument('--targeted-hull-overrides',action='store_true')
    args=parser.parse_args()
    if args.targeted_hull_overrides:
        targeted_hull_overrides()
    else:
        if args.include_sample_thirteen:sample_thirteen()
        calendar_polygons()
