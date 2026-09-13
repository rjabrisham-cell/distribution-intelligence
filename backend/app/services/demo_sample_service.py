"""Allowlist public presentation data; never forward the internal audit context."""
import json
from pathlib import Path
from fastapi import HTTPException


def prepared_sample_context(project_id):
    """Serve only the reviewed presentation snapshot; never run an audit on GET."""
    payload = json.loads(Path(__file__).with_name('demo_tehran_snapshot.json').read_text(encoding='utf-8'))
    if project_id != payload['source_project']:
        raise HTTPException(503, 'نمونه آماده برای این تنظیم موجود نیست.')
    return payload['context']


def public_sample_context(context):
    summary_keys = {"total_stores", "ready_stores", "review_stores", "invalid_stores", "missing_coordinate_stores",
                    "stores_with_coordinates", "stores_without_coordinates", "matched_to_master", "unmatched_to_master",
                    "percentage", "status"}
    summary = {k: v for k, v in (context.get("readiness_summary") or {}).items() if k in summary_keys}
    geo = json.loads(context.get("map_geojson_json") or '{"features": []}')
    features = []
    for index, feature in enumerate(geo.get("features", []), 1):
        props = feature.get("properties", {})
        features.append({"type": "Feature", "geometry": feature["geometry"], "properties": {
            "title": f"نقطه فروش نمونه {index}",
            "readiness_status": props.get("readiness_status"),
            "matched_to_master": bool(props.get("matched_to_master")), "cluster_weight": 1,
        }})
    matching = context.get("matching_summary") or {}
    # Representative rows contain only categorical information, never source fields.
    groups = {}
    for feature in features:
        p = feature['properties']
        status = p.get('readiness_status') or 'NEEDS_REVIEW'
        groups.setdefault(status, []).append({'status': status, 'matched': p['matched_to_master'], 'coordinates': True})
    missing = (context.get('audit_run') or {}).get('missing_coordinate_rows', [])
    if missing:
        groups['NEEDS_GEOCODING'] = [{'status':'NEEDS_GEOCODING', 'matched': None, 'coordinates':False} for _ in missing[:5]]
    rows = []
    for i in range(5):
        for group in groups.values():
            if i < len(group): rows.append(group[i])
    rows = rows[:20]
    report = {"sections": [{"name": section["name"], "percentage": section.get("percentage")}
                            for section in (context.get("report") or {}).get("sections", [])
                            if section.get("name") in {"completeness", "validity", "duplicates"}]}
    return {"demo_sample": True, "public_demo": True, "sample_rows": rows, "project_context": {"name": "نمونه شبکه پخش تهران"},
            "readiness_summary": summary, "report": report, "audit_run": None,
            "matching_summary": {k: matching.get(k, 0) for k in ("processed", "confirmed_matches")},
            "map_geojson_json": json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
            "message": "نمونه عمومی شبکه پخش تهران؛ اطلاعات تماس و جزئیات رکوردها نمایش داده نمی‌شود."}
