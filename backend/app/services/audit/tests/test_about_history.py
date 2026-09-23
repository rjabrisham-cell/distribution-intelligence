"""Public history boundary and curated data checks; no operational DB access."""
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from app.core.demo_security import DemoSecurityMiddleware
from app.routers.home import router

APP = Path(__file__).resolve().parents[3]
DATA = APP / 'static/data/history/kaleh'


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.mount('/static', StaticFiles(directory=APP / 'static'), name='static')
    app.add_middleware(DemoSecurityMiddleware, raise_errors=True)
    with TestClient(app, follow_redirects=False) as test:
        yield test


def test_anonymous_page_contains_complete_narrative_without_javascript(client):
    assert not client.cookies
    response = client.get('/about')
    assert response.status_code == 200
    for text in ['تهران ایستا','تهران هوشمند','تهران داینامیک', 'یک لایه هوشمند روی تهران', 'نمونه اجرایی']:
        assert text in response.text
    assert '/static/logo/DIPLogo.webp' in response.text
    assert 'href="/about"' in response.text
    assert 'href="/demo/trial"' in response.text
    assert '<noscript>' in response.text
    assert '<!DOCTYPE html>' in response.text
    assert 'نمایشی' not in response.text
    assert 'شهر ثابت ← لایه هوشمند روزانه ← عملیات در حرکت' not in response.text
    assert response.text.count('id="history-calendar-days"')==1
    assert response.text.index('id="history-story"') < response.text.index('id="history-calendar-days"') < response.text.index('class="history-steps"')


@pytest.mark.parametrize('name',['history-summary.json','legacy-regions.geojson','planned-routes.geojson','gps-tracks.geojson','smart-regions.geojson','smart-summary.json','municipal-regions.geojson','operation-tracks.geojson','access-routes.geojson','gps-continuity.geojson'])
def test_only_curated_assets_are_public(client, name):
    response = client.get('/static/data/history/kaleh/' + name)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.parametrize('path',[
    '/static/data/history/kaleh/Tourism.mdb','/static/data/history/kaleh/Log.zip',
    '/static/data/history/kaleh/private.csv','/data/history/kaleh/source/Tourism.mdb',
    '/static/data/history/kaleh/extraction-report.json',
])
def test_raw_or_unlisted_data_is_not_public(client, path):
    assert client.get(path).status_code == 404


def test_other_security_boundaries_unchanged(client):
    assert client.get('/projects').status_code == 303
    assert client.post('/about').status_code == 403


def test_public_data_schema_privacy_budget_and_timing():
    summary=json.loads((DATA/'history-summary.json').read_text())
    assert summary['customer_archive_count']==9750
    assert summary['route_count']==16 and summary['legacy_region_count']==22
    assert summary['planned_record_count']==667
    assert summary['legacy_geometry']=='illustrative_service_patches_inside_administrative_boundaries'
    regions=json.loads((DATA/'legacy-regions.geojson').read_text())['features']
    assert len(regions)==22
    assert {f['properties']['region'] for f in regions}==set(range(1,23))
    assert all(f['geometry']['type'] in {'Polygon','MultiPolygon'} and set(f['properties'])=={'region','kind','label_center'} for f in regions)
    planned=json.loads((DATA/'planned-routes.geojson').read_text())['features']
    tracks=json.loads((DATA/'gps-tracks.geojson').read_text())['features']
    assert {f['properties']['route'] for f in tracks}==set(range(1,17))
    assert len(planned)==len(tracks)==16
    for f in planned:
        assert set(f['properties'])=={'route','color','store_count','load_share','center'}
        assert f['geometry']['type']=='Polygon'
    count=0
    for f in tracks:
        assert set(f['properties'])=={'route','color','times'}
        assert f['geometry']['type']=='MultiLineString'
        assert len(f['geometry']['coordinates'])==len(f['properties']['times'])
        end=-1
        for segment,times in zip(f['geometry']['coordinates'],f['properties']['times']):
            assert len(segment)==len(times)>=2
            assert times==sorted(times) and times[0]>=end
            end=times[-1]
            count+=len(segment)
            for lon,lat in segment:
                assert 50.8<=lon<=51.85 and 35.35<=lat<=36.05
                assert lon==round(lon,3) and lat==round(lat,3)
    assert count==summary['gps_point_count']
    # Complete official boundaries plus unsimplified operations and road access.
    assert sum(p.stat().st_size for p in DATA.iterdir() if p.is_file())<800_000
    assert {p.suffix for p in DATA.rglob('*') if p.is_file()}=={'.json','.geojson'}


def test_display_regions_and_fixed_allocation():
    from shapely.geometry import shape, Point
    official=json.loads((DATA/'municipal-regions.geojson').read_text())['features']
    assert {f['properties']['region'] for f in official}==set(range(1,23))
    assert all(shape(f['geometry']).is_valid for f in official)
    for name, count in [('legacy-regions.geojson',22),('smart-regions.geojson',16)]:
        features=json.loads((DATA/name).read_text())['features']
        assert len(features)==count
        for feature in features:
            geometry=shape(feature['geometry'])
            assert geometry.is_valid and not geometry.is_empty
            assert geometry.covers(Point(feature['properties']['label_center']))
        # Requested broad hulls may overlap; never clip away recorded operations.
    summary=json.loads((DATA/'smart-summary.json').read_text())
    assert len(summary['groups'])==16
    assert {g['group'] for g in summary['groups']}==set(range(1,17))
    assert sum(g['store_count'] for g in summary['groups'])==798


def test_calendar_public_dates_and_road_connections(client):
    index=json.loads((DATA/'calendar/index.json').read_text())
    assert len({d['vehicles'] for d in index['days']})>=3
    for day in index['days']:
        assert client.get('/static/data/history/kaleh/calendar/'+day['file']).status_code==200
        tracks=json.loads((DATA/'calendar'/day['file']).read_text())['features']
        access=json.loads((DATA/'calendar'/(day['date']+'-access.geojson')).read_text())['features']
        assert len(tracks)==len(access)==day['vehicles']
        for f,a in zip(tracks,access):
            assert a['geometry']['coordinates'][0]==[51.554142,35.729941]
            assert a['geometry']['coordinates'][-1]==f['geometry']['coordinates'][0][0]
            assert set(f['properties'])=={'route','color','times'}
            for coordinates,times in zip(f['geometry']['coordinates'],f['properties']['times']):
                assert len(coordinates)==len(times)
                assert times==sorted(times) and all(0<=t<86400 for t in times)
    assert client.get('/static/data/history/kaleh/calendar/2099-01-01.geojson').status_code==404
    assert client.get('/static/data/history/kaleh/calendar/private.csv').status_code==404


def test_sample_access_continuity_and_service_eleven():
    from shapely.geometry import shape
    access=json.loads((DATA/'access-routes.geojson').read_text())['features']
    gaps=json.loads((DATA/'gps-continuity.geojson').read_text())['features']
    operations=json.loads((DATA/'operation-tracks.geojson').read_text())['features']
    assert len(access)==len(operations)==16
    assert all(f['properties'].get('after_segment',0)>=0 for f in gaps)
    for f in operations:
        route=f['properties']['route']; segments=f['geometry']['coordinates']
        a=next(a for a in access if a['properties']['route']==route and a['properties']['kind']=='routed_access_not_recorded_gps')
        assert len(a['geometry']['coordinates'])>=2
        if len(a['geometry']['coordinates'])==2:
            assert a['properties']['distance']<30  # A short OSRM road edge, not a cross-city chord.
        assert a['geometry']['coordinates'][0]==[51.554142,35.729941]
        assert a['geometry']['coordinates'][-1]==segments[0][0]
        points=a['geometry']['coordinates']
        edges=[tuple(sorted((tuple(x),tuple(y)))) for x,y in zip(points,points[1:]) if x!=y]
        assert len(edges)==len(set(edges))
        for i,(left,right) in enumerate(zip(segments,segments[1:])):
            if left[-1]==right[0]:continue
            gap=next(a for a in gaps if a['properties']['route']==route and a['properties'].get('after_segment')==i)
            assert gap['geometry']['coordinates'][0]==left[-1]
            assert gap['geometry']['coordinates'][-1]==right[0]
    regions=json.loads((DATA/'smart-regions.geojson').read_text())['features']
    west=shape(next(f['geometry'] for f in regions if f['properties']['group']==11))
    assert west.bounds[2]<51.02 and west.bounds[2]-west.bounds[0]>.2


def test_full_operational_gps_and_uniform_ten_percent_buffer():
    from shapely.geometry import MultiPoint, Point, shape
    from shapely.ops import transform
    from pyproj import Transformer
    project=Transformer.from_crs(4326,32639,always_xy=True).transform
    original=json.loads((DATA/'gps-tracks.geojson').read_text())['features']
    operations=json.loads((DATA/'operation-tracks.geojson').read_text())['features']
    polygons=json.loads((DATA/'smart-regions.geojson').read_text())['features']
    for source,operation,polygon in zip(original,operations,polygons):
        route=source['properties']['route'];segments=source['geometry']['coordinates']
        times=source['properties']['times']
        assert route==operation['properties']['route']==polygon['properties']['group']
        if route==11:
            segments=segments[1:3];times=times[1:3]
        elif route==15:
            indices=[i for i,xy in enumerate(segments[0]) if xy[0]<=51.35]
            a,b=min(indices),max(indices)
            segments=[segments[0][a:b+1]];times=[times[0][a:b+1]]
        elif route==13:
            assert operation['properties']['source']=='synthetic_demo'
            assert polygon['properties']['source']=='synthetic_demo'
            segments=operation['geometry']['coordinates'];times=operation['properties']['times']
        assert operation['geometry']['coordinates']==segments
        assert operation['properties']['times']==times
        points=[project(*xy) for segment in segments for xy in segment]
        hull=MultiPoint(points).convex_hull
        area=transform(project,shape(polygon['geometry']))
        assert area.covers(hull)
        assert area.area/hull.area==pytest.approx(1.1,abs=1e-7)
        if route==11:
            access=json.loads((DATA/'access-routes.geojson').read_text())['features'][10]
            road=transform(project,shape(access['geometry']))
            for waypoint in [[51.409828,35.614663],[51.321,35.627]]:
                assert road.distance(Point(project(*waypoint)))<120


def test_calendar_polygons_match_each_day_and_preserve_operation_branches(client):
    from shapely.geometry import MultiPoint, shape
    from shapely.ops import transform
    from pyproj import Transformer
    project=Transformer.from_crs(4326,32639,always_xy=True).transform
    index=json.loads((DATA/'calendar/index.json').read_text())
    for date,count in [('2010-04-21',15),('2010-04-22',15),('2010-04-24',14),('2010-04-25',11)]:
        response=client.get('/static/data/history/kaleh/calendar/'+date+'-regions.geojson')
        assert response.status_code==200
        polygons=response.json()['features']
        tracks=json.loads((DATA/'calendar'/(date+'.geojson')).read_text())['features']
        day=next(d for d in index['days'] if d['date']==date)
        cards={c['group']:c for c in day['display']['groups']}
        assert len(polygons)==len(tracks)==count
        for polygon,track in zip(polygons,tracks):
            p=polygon['properties'];route=track['properties']['route']
            assert p['group']==route
            assert p['color']==track['properties']['color']==cards[route]['color']
            assert p['store_count']==cards[route]['store_count']
            points=[]
            for segment,a,b in p['operation_spans']:
                assert 0<=a<b<len(track['geometry']['coordinates'][segment])
                points.extend(project(*xy) for xy in track['geometry']['coordinates'][segment][a:b+1])
            hull=MultiPoint(points).convex_hull
            geometry=transform(project,shape(polygon['geometry']))
            assert geometry.covers(hull)
            assert geometry.area/hull.area==pytest.approx(1.1,abs=1e-6)
    assert client.get('/static/data/history/kaleh/calendar/2010-04-20-regions.geojson').status_code==404


def test_synthetic_thirteen_covers_both_target_districts():
    from shapely.geometry import Point, shape
    operation=json.loads((DATA/'operation-tracks.geojson').read_text())['features'][12]
    access=json.loads((DATA/'access-routes.geojson').read_text())['features'][12]
    assert operation['properties']['source']=='synthetic_demo'
    assert access['properties']['source']=='routed_from_recorded_access_corridor'
    coordinates=operation['geometry']['coordinates'][0]
    assert access['geometry']['coordinates'][-1]==coordinates[0]
    official={f['properties']['region']:shape(f['geometry']) for f in json.loads((DATA/'municipal-regions.geojson').read_text())['features']}
    for region in (5,22):
        assert sum(official[region].covers(Point(xy)) for xy in coordinates)>20


def test_four_days_are_complete_suffixes_with_separate_access(client):
    from shapely.geometry import shape, LineString
    from shapely.ops import transform
    from pyproj import Transformer
    project=Transformer.from_crs(4326,32639,always_xy=True).transform
    for date,count in [('2010-04-21',15),('2010-04-22',15),('2010-04-24',14),('2010-04-25',11)]:
        response=client.get('/static/data/history/kaleh/calendar/'+date+'-operations.geojson')
        assert response.status_code==200
        features=response.json()['features']
        operations=[f for f in features if f['properties']['type']=='operational_gps']
        assert len(operations)==count
        original=json.loads((DATA/'calendar'/(date+'.geojson')).read_text())['features']
        roads=json.loads((DATA/'calendar'/(date+'-access.geojson')).read_text())['features']
        polygons=json.loads((DATA/'calendar'/(date+'-regions.geojson')).read_text())['features']
        for source,operation,polygon,road in zip(original,operations,polygons,roads):
            route=source['properties']['route'];spans=polygon['properties']['operation_spans']
            remaining=sum(map(len,source['geometry']['coordinates']))-sum(map(len,operation['geometry']['coordinates']))
            start_segment=0
            while remaining>=len(source['geometry']['coordinates'][start_segment]):
                remaining-=len(source['geometry']['coordinates'][start_segment]);start_segment+=1
            start_point=remaining
            display_spans=[[i,start_point if i==start_segment else 0,len(s)-1]
                           for i,s in enumerate(source['geometry']['coordinates']) if i>=start_segment]
            expected=[source['geometry']['coordinates'][s][a:b+1] for s,a,b in display_spans]
            assert operation['geometry']['coordinates']==expected
            assert operation['properties']['times']==[source['properties']['times'][s][a:b+1] for s,a,b in display_spans]
            prefix_count=sum(len(s) for s in source['geometry']['coordinates'][:start_segment])+start_point
            raw=[p for s in source['geometry']['coordinates'] for p in s]
            assert [p for s in expected for p in s]==raw[prefix_count:]
            assert sum(len(s) for s in expected)+prefix_count==len(raw)
            computed=next(f for f in features if f['properties']['route']==route and f['properties']['source']=='computed_road_network')
            assert computed['geometry']==road['geometry']
            assert computed['properties']['type']=='access_route'
            geometry=transform(project,shape(polygon['geometry'])).buffer(.00001)
            window=[source['geometry']['coordinates'][s][a:b+1] for s,a,b in spans]
            window_points=[p for line in window for p in line]
            hull_segment,hull_point,_=spans[0]
            hull_prefix=sum(len(s) for s in source['geometry']['coordinates'][:hull_segment])+hull_point
            assert window_points==raw[hull_prefix:hull_prefix+len(window_points)]
            for line in window:
                assert geometry.covers(LineString([project(*xy) for xy in line]))
    assert client.get('/static/data/history/kaleh/calendar/2010-04-20-operations.geojson').status_code==404


def test_first_stop_is_conservative_and_never_removes_later_branches(monkeypatch):
    monkeypatch.syspath_prepend(str(APP.parents[1]/'tools/history'))
    from prepare_day_polygons import classify_prefix
    points=[[51.52,35.72],[51.50,35.72],[51.48,35.72],
            [51.45,35.70],[51.4501,35.70],[51.4502,35.70],[51.45,35.70],
            [51.20,35.75],[51.60,35.80]]
    track={'geometry':{'coordinates':[points,[[51.6,35.8],[51.3,35.7]]]},
           'properties':{'times':[[0,60,120,180,240,300,360,420,480],[600,660]]}}
    spans,stop,prefix,reason=classify_prefix(track)
    assert prefix==3 and stop['duration_seconds']==180 and stop['samples']==4
    assert spans==[[0,3,8],[1,0,1]]  # Even later fast highway and return branches remain.
    assert reason=='first_sustained_stop'
    track['properties']['times']=[[0,60,120,180,181,182,183,240,300],[600,660]]
    spans,stop,prefix,_=classify_prefix(track)
    assert stop is None and prefix==0 and spans==[[0,0,8],[1,0,1]]
    track['properties']['times']=[[0,60,120,180,600,1200,1800,2400,3000],[3600,4200]]
    spans,stop,prefix,_=classify_prefix(track)
    assert stop is None and prefix==0  # Sparse timing cannot establish a stop.


def test_hull_return_window_preserves_display_and_uses_latest_stop(monkeypatch):
    monkeypatch.syspath_prepend(str(APP.parents[1]/'tools/history'))
    from prepare_day_polygons import classify_window
    from copy import deepcopy
    points=[[51.54,35.72],[51.50,35.71]]
    points += [[51.45,35.70],[51.4501,35.70],[51.45,35.7001],[51.45,35.70]]
    points += [[51.42,35.69],[51.40,35.70],[51.4001,35.70],[51.40,35.7001],[51.40,35.70]]
    points += [[51.45,35.71],[51.50,35.72],[51.554142,35.729941]]
    track={'geometry':{'coordinates':[points]},'properties':{'times':[list(range(0,len(points)*60,60))]}}
    result=classify_window(track)
    assert result[0]==[[0,2,13]]  # Display retains the entire return journey.
    assert result[1]==[[0,2,10]] and result[3]['record_1based']==8
    assert result[4:6]==(2,3)
    assert result[7]=='continuous_return_after_last_valid_stop'
    away=deepcopy(track);away['geometry']['coordinates'][0][-1]=[51.50,35.72]
    assert classify_window(away)[5]==0
    gap=deepcopy(track);gap['properties']['times'][0][-1]+=300
    assert classify_window(gap)[5]==0
    detour=deepcopy(track);detour['geometry']['coordinates'][0][-2]=[51.20,35.65]
    assert classify_window(detour)[5]==0
