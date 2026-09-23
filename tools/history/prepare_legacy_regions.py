"""Create illustrative service patches, not administrative or observed service boundaries.

Reads only the supplied local.zip. No operational database or historical archives.
"""
import json
import math
import struct
import zipfile
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.ops import transform, nearest_points

ROOT = Path(__file__).resolve().parents[2]
CENTERS = [
    (51.434268951416016,35.8044292887966),(51.366119384765625,35.75178648406282),
    (51.4284610748291,35.77583414020995),(51.514434814453125,35.74997539731552),
    (51.31685256958008,35.75304028920634),(51.4061164855957,35.72893590886671),
    (51.439247131347656,35.72837849583882),(51.49314880371094,35.725591372187246),
    (51.34045600891113,35.6891407584666),(51.36268615722656,35.686700829862694),
    (51.39101028442383,35.68419111115593),(51.42414093017578,35.68251792148951),
    (51.47581100463867,35.702524181980145),(51.486496925354004,35.67892741689899),
    (51.47512435913086,35.63732853921192),(51.40336990356445,35.640397763258306),
    (51.360111236572266,35.65630003612433),(51.31522178649902,35.65741586622914),
    (51.37144088745117,35.633282563779396),(51.43341064453125,35.60216356588302),
    (51.21986389160156,35.70524241542319),(51.23136520385742,35.74133733970409),
]


def boundaries():
    # Minimal ESRI Polygon/DBF reader for this fixed source; no dependency install.
    with zipfile.ZipFile(ROOT/'data/history/kaleh/source/local.zip') as archive:
        dbf, shp = archive.read('local.dbf'), archive.read('local.shp')
    count, header, width = struct.unpack_from('<IHH', dbf, 4)
    fields = [(dbf[i:i+11].split(b'\0')[0].decode(), dbf[i+16])
              for i in range(32, header-1, 32)]
    offset = 100
    result = {}
    for index in range(count):
        length = struct.unpack_from('>I', shp, offset+4)[0]*2
        record = shp[offset+8:offset+8+length]; offset += 8+length
        assert struct.unpack_from('<I', record)[0] == 5
        row = dbf[header+index*width:header+(index+1)*width]
        values = {}; start = 1
        for name, size in fields:
            values[name] = row[start:start+size].decode().strip(); start += size
        region = int(values['BOUNDRY_ID'])
        if region == 0:  # Extra record: ID=15, BOUNDRY_ID=0; not a numbered district.
            continue
        assert 1 <= region <= 22 and region not in result
        parts, points = struct.unpack_from('<II', record, 36)
        indexes = list(struct.unpack_from('<'+'I'*parts, record, 44))+[points]
        coordinates = [struct.unpack_from('<dd', record, 44+4*parts+16*i) for i in range(points)]
        polygon = Polygon()
        for a,b in zip(indexes, indexes[1:]):
            polygon = polygon.symmetric_difference(Polygon(coordinates[a:b]).buffer(0))
        result[region] = polygon
    assert set(result) == set(range(1,23))
    return result


def main():
    forward = Transformer.from_crs(4326,32639,always_xy=True).transform
    backward = Transformer.from_crs(32639,4326,always_xy=True).transform
    features = []; inside = 0; maximum_shift = 0
    for region, boundary in sorted(boundaries().items()):
        center = Point(forward(*CENTERS[region-1]))
        inside += boundary.covers(center)
        interior = boundary.buffer(-60)
        if not interior.covers(center):
            center = nearest_points(interior,center)[0]
        maximum_shift = max(maximum_shift,center.distance(Point(forward(*CENTERS[region-1]))))
        radius = min(1400, math.sqrt(boundary.area)*.16)
        ring = []
        for i in range(64):
            angle = i*2*math.pi/64
            r = radius*(1+.14*math.sin(3*angle+region)+.09*math.cos(5*angle-region))
            ring.append((center.x+r*math.cos(angle),center.y+r*(.65+.025*(region%9))*math.sin(angle)))
        patch = Polygon(ring).intersection(boundary.buffer(-10)).simplify(10,preserve_topology=True)
        if patch.geom_type == 'MultiPolygon': patch = max(patch.geoms,key=lambda p:p.area)
        assert patch.is_valid and not patch.is_empty and boundary.covers(patch)
        assert patch.area < boundary.area*.25
        geometry = mapping(transform(backward,patch))
        # Round only the display geometry; verify containment again after serialization.
        geometry = json.loads(json.dumps(geometry),parse_float=lambda v:round(float(v),6))
        assert boundary.covers(transform(forward,shape(geometry)))
        features.append({'type':'Feature','properties':{'region':region},'geometry':geometry})
    dest = ROOT/'backend/app/static/data/history/kaleh'
    (dest/'legacy-regions.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},separators=(',',':'))+'\n',encoding='utf-8')
    summary = json.loads((dest/'history-summary.json').read_text())
    summary['legacy_geometry'] = 'illustrative_service_patches_inside_administrative_boundaries'
    (dest/'history-summary.json').write_text(json.dumps(summary,separators=(',',':'))+'\n',encoding='utf-8')
    print(f'22 valid contained patches; supplied centers inside own boundary: {inside}/22; maximum adjustment: {maximum_shift:.0f} m')


if __name__ == '__main__':
    main()
