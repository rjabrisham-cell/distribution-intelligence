"""Characterization tests for the DIP Matching -> Readiness boundary."""

from types import SimpleNamespace

from app.services.audit.audit_runner import AuditRunner


def _company(**overrides):
    values = {
        "id": 21,
        "master_store_id": None,
        "name": "فروشگاه ورودی",
        "phone": "02112345678",
        "address": "آدرس خام شرکت",
        "postal_code": None,
        "latitude": None,
        "longitude": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _evidence(**overrides):
    values = {
        "normalized_address": "آدرس نرمال‌شده ورودی",
        "address_text": "آدرس خام اکسل",
        "postal_code": "1234567890",
        "normalized_latitude": 35.7001,
        "normalized_longitude": 51.4001,
        "latitude": 35.7002,
        "longitude": 51.4002,
        "source_id": "import_batch:7:row:12",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _master(**overrides):
    values = {
        "canonical_name": "فروشگاه مستر",
        "manager_name": "مدیر مستر",
        "canonical_phone": "02199999999",
        "mobile": "09120000000",
        "province_id": 8,
        "city_id": 301,
        "address": "آدرس قطعی مستر",
        "postal_code": "9876543210",
        "plaque": "15",
        "unit": "2",
        "floor": "1",
        "latitude": 35.7211,
        "longitude": 51.4211,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_confirmed_master_is_authoritative_for_readiness():
    view = AuditRunner._build_store_view(
        _company(master_store_id=9001, latitude=35.1, longitude=51.1),
        _master(),
        _evidence(),
    )

    assert view.master_store_id == 9001
    assert view.canonical_name == "فروشگاه مستر"
    assert view.address == "آدرس قطعی مستر"
    assert view.latitude == 35.7211
    assert view.longitude == 51.4211


def test_unmatched_store_uses_normalized_import_evidence():
    view = AuditRunner._build_store_view(
        _company(),
        None,
        _evidence(),
    )

    assert view.master_store_id is None
    assert view.canonical_name == "فروشگاه ورودی"
    assert view.address == "آدرس نرمال‌شده ورودی"
    assert view.latitude == 35.7001
    assert view.longitude == 51.4001
    assert view.source_id == "import_batch:7:row:12"


def test_company_coordinates_are_last_safe_fallback():
    view = AuditRunner._build_store_view(
        _company(latitude=35.65, longitude=51.35),
        None,
        _evidence(
            normalized_latitude=None,
            normalized_longitude=None,
            latitude=None,
            longitude=None,
        ),
    )

    assert view.latitude == 35.65
    assert view.longitude == 51.35


def test_geojson_uses_longitude_latitude_and_master_identity():
    view = AuditRunner._build_store_view(
        _company(master_store_id=9001),
        _master(),
        _evidence(),
    )
    row = {
        "store": view,
        "status": "Ready",
        "coordinate_status": "valid",
        "reasons": [],
        "completeness": SimpleNamespace(percentage=100.0),
        "validity": SimpleNamespace(percentage=100.0),
        "duplicate": SimpleNamespace(
            status=SimpleNamespace(value="unique")
        ),
    }

    feature = AuditRunner._build_geojson([row])["features"][0]

    assert feature["geometry"]["coordinates"] == [51.4211, 35.7211]
    assert feature["properties"]["store_id"] == 9001
    assert feature["properties"]["company_store_id"] == 21
    assert feature["properties"]["matched_to_master"] is True


def test_missing_coordinate_row_stays_available_for_future_geocoding():
    view = AuditRunner._build_store_view(
        _company(),
        None,
        _evidence(
            normalized_latitude=None,
            normalized_longitude=None,
            latitude=None,
            longitude=None,
        ),
    )
    row = {
        "store": view,
        "status": "MissingCoordinate",
        "reasons": ["latitude_missing", "longitude_missing"],
    }

    missing = AuditRunner._build_missing_coordinate_rows([row])[0]

    assert missing["source_row"] == 12
    assert missing["master_store_id"] is None
    assert missing["missing_fields"] == ["latitude", "longitude"]
    assert missing["has_address_for_geocoding"] is True
