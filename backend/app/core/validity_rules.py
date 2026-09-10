# ============================================================================
# Distribution Intelligence Platform (DIP)
# Sprint 2 – Data Quality Audit Engine
# Contract v2.0 (Frozen — three-tier weight contract)
#
# Validity Rules – Single Source of Truth for Validity Checks
# ============================================================================
# ALL rules are STATELESS, NO DB, NO Session, NO Business Decisions.
# Each rule receives a Store instance and returns a dict of
# field_name → ValidationVerdict.
# ============================================================================

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.models.store import Store
from app.core.field_profile import ValidationVerdict


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    V E R D I C T   P R I O R I T Y                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# Highest priority wins when merging conflicting rule verdicts for the same field.
# INVALID takes precedence over WARNING, which takes precedence over UNKNOWN, etc.
VERDICT_PRIORITY: dict[ValidationVerdict, int] = {
    ValidationVerdict.INVALID: 3,
    ValidationVerdict.WARNING: 2,
    ValidationVerdict.UNKNOWN: 1,
    ValidationVerdict.VALID:   0,
}


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                           R U L E   C O N T R A C T                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

RuleFunc = Callable[["Store"], dict[str, ValidationVerdict]]


@dataclass(frozen=True, slots=True)
class ValidityRule:
    """
    A named validity rule with a stateless check function.

    Parameters
    ----------
    rule_name : str
        Unique snake_case identifier for this rule.
    description : str
        Human-readable description of what the rule checks.
    priority : int
        Execution priority (lower = earlier). Default 100.
    metadata : dict
        Arbitrary metadata for future AI/Recommendation engines
        (e.g. distance thresholds, expected precision, etc.).
    check : RuleFunc
        Stateless callable: Store → dict[field_name, ValidationVerdict].
    """

    rule_name:   str
    description: str
    check:       RuleFunc
    priority:    int = 100
    metadata:    dict[str, Any] = field(default_factory=dict)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                  P U R E   R U L E   F U N C T I O N S                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def _is_present(value: Any) -> bool:
    """Helper: value is not None and not an empty/whitespace string."""
    if value is None:
        return False

    if isinstance(value, str) and not value.strip():
        return False

    return True


# ── Iran Phone ─────────────────────────────────────────────────────────────

_MOBILE_RE = re.compile(r"^09\d{9}$")
_PHONE_LINE_RE = re.compile(r"^0\d{2,3}-?\d{7,8}$")


def rule_iran_phone(store: Store) -> dict[str, ValidationVerdict]:
    """
    Check landline (canonical_phone) and mobile for Iranian phone patterns.

    Contract v2.0 — aligned to real Store columns:
      - ``canonical_phone`` → landline, validated with _PHONE_LINE_RE
      - ``mobile``          → mobile, validated with _MOBILE_RE

    NOTE (business decision deferred to completeness layer):
    neither empty landline NOR empty mobile is marked INVALID here; they are
    WARNING so that the "at least one of phone/mobile" rule can be evaluated
    at the completeness level. This preserves prior non-blocking behavior.
    """
    results: dict[str, ValidationVerdict] = {}

    phone = getattr(store, "canonical_phone", None)

    if not _is_present(phone):
        results["canonical_phone"] = ValidationVerdict.WARNING
    elif _PHONE_LINE_RE.match(str(phone).strip().replace(" ", "")):
        results["canonical_phone"] = ValidationVerdict.VALID
    else:
        results["canonical_phone"] = ValidationVerdict.INVALID

    mobile = getattr(store, "mobile", None)

    if not _is_present(mobile):
        results["mobile"] = ValidationVerdict.WARNING
    elif _MOBILE_RE.match(str(mobile).strip()):
        results["mobile"] = ValidationVerdict.VALID
    else:
        results["mobile"] = ValidationVerdict.INVALID

    return results


# ── Postal Code ────────────────────────────────────────────────────────────

_POSTAL_RE = re.compile(r"^\d{10}$")


def rule_iran_postal_code(store: Store) -> dict[str, ValidationVerdict]:
    """Check 10-digit Iranian postal code format."""
    pc = getattr(store, "postal_code", None)

    if not _is_present(pc):
        return {"postal_code": ValidationVerdict.WARNING}

    return {
        "postal_code": (
            ValidationVerdict.VALID
            if _POSTAL_RE.match(str(pc).strip())
            else ValidationVerdict.INVALID
        )
    }


# ── Coordinate Range ───────────────────────────────────────────────────────

def rule_coordinate_range(store: Store) -> dict[str, ValidationVerdict]:
    """
    Validate latitude (-90 … 90) and longitude (-180 … 180).
    Also reject values very close to zero (common import error).
    """
    results: dict[str, ValidationVerdict] = {}

    for field, min_val, max_val in [
        ("latitude", -90.0, 90.0),
        ("longitude", -180.0, 180.0),
    ]:
        val = getattr(store, field, None)

        if not _is_present(val):
            results[field] = ValidationVerdict.INVALID
            continue

        try:
            f = float(val)
        except (TypeError, ValueError):
            results[field] = ValidationVerdict.INVALID
            continue

        if abs(f) <= 0.000_001:
            results[field] = ValidationVerdict.INVALID
        elif min_val <= f <= max_val:
            results[field] = ValidationVerdict.VALID
        else:
            results[field] = ValidationVerdict.INVALID

    return results


# ── Coordinate Precision ───────────────────────────────────────────────────

def rule_coordinate_precision(store: Store) -> dict[str, ValidationVerdict]:
    """
    Check decimal precision of lat/lon values.
    >= 5 decimal places → VALID
    3-4 decimal places  → WARNING (low precision, ~100m-1km accuracy)
    < 3 decimal places  → INVALID (insufficient precision for geo-analysis)
    """
    results: dict[str, ValidationVerdict] = {}

    for field in ("latitude", "longitude"):
        raw = getattr(store, field, None)

        if not _is_present(raw):
            results[field] = ValidationVerdict.UNKNOWN
            continue

        try:
            s = str(float(raw))
        except (TypeError, ValueError):
            results[field] = ValidationVerdict.INVALID
            continue

        if "." not in s:
            results[field] = ValidationVerdict.INVALID
            continue

        decimals = len(s.split(".")[1])

        if decimals >= 5:
            results[field] = ValidationVerdict.VALID
        elif decimals >= 3:
            results[field] = ValidationVerdict.WARNING
        else:
            results[field] = ValidationVerdict.INVALID

    return results


# ── Coordinates in Iran (rough bounding box) ───────────────────────────────

_IRAN_LAT_MIN, _IRAN_LAT_MAX = 24.0, 40.0
_IRAN_LON_MIN, _IRAN_LON_MAX = 44.0, 64.0


def rule_coordinate_in_iran(store: Store) -> dict[str, ValidationVerdict]:
    """
    Check that lat/lon fall inside a rough bounding box of Iran
    (24°–40° N, 44°–64° E).
    """
    results: dict[str, ValidationVerdict] = {}

    for field, min_v, max_v in [
        ("latitude", _IRAN_LAT_MIN, _IRAN_LAT_MAX),
        ("longitude", _IRAN_LON_MIN, _IRAN_LON_MAX),
    ]:
        raw = getattr(store, field, None)

        if not _is_present(raw):
            results[field] = ValidationVerdict.INVALID
            continue

        try:
            f = float(raw)
        except (TypeError, ValueError):
            results[field] = ValidationVerdict.INVALID
            continue

        if min_v <= f <= max_v:
            results[field] = ValidationVerdict.VALID
        else:
            results[field] = ValidationVerdict.INVALID

    return results


# ── Coordinate Swap Detection ──────────────────────────────────────────────

def rule_coordinate_swap_detection(
    store: Store,
) -> dict[str, ValidationVerdict]:
    """
    Detect if latitude and longitude values may have been swapped
    (lat in lon range and vice-versa). This is a WARNING, not INVALID,
    because the pair could still be correct for a location outside Iran.
    """
    results: dict[str, ValidationVerdict] = {}

    lat_raw = getattr(store, "latitude", None)
    lon_raw = getattr(store, "longitude", None)

    if not _is_present(lat_raw) or not _is_present(lon_raw):
        results["latitude"] = ValidationVerdict.UNKNOWN
        results["longitude"] = ValidationVerdict.UNKNOWN
        return results

    try:
        lat = float(lat_raw)
        lon = float(lon_raw)
    except (TypeError, ValueError):
        results["latitude"] = ValidationVerdict.UNKNOWN
        results["longitude"] = ValidationVerdict.UNKNOWN
        return results

    lat_in_lon_range = _IRAN_LON_MIN <= lat <= _IRAN_LON_MAX
    lon_in_lat_range = _IRAN_LAT_MIN <= lon <= _IRAN_LAT_MAX

    if lat_in_lon_range and lon_in_lat_range:
        results["latitude"] = ValidationVerdict.WARNING
        results["longitude"] = ValidationVerdict.WARNING
    else:
        results["latitude"] = ValidationVerdict.UNKNOWN
        results["longitude"] = ValidationVerdict.UNKNOWN

    return results


# ── Province / City ID positivity ──────────────────────────────────────────

def rule_province_city_id_positive(
    store: Store,
) -> dict[str, ValidationVerdict]:
    """
    Ensure geographic base ID fields are positive.

    Contract v2.0 — aligned to real Store columns (no ``region_id``):
      - ``province_id`` / ``city_id`` → must be > 0 (blocking)

    NOTE (MVP scope): county_id / district_id / neighborhood_id / village_id
    are removed from MVP and no longer validated here.
    """
    results: dict[str, ValidationVerdict] = {}

    def _check_int(field_name: str) -> ValidationVerdict:
        val = getattr(store, field_name, None)

        if not _is_present(val):
            return ValidationVerdict.INVALID

        try:
            n = int(val)
        except (TypeError, ValueError):
            return ValidationVerdict.INVALID

        return (
            ValidationVerdict.VALID
            if n > 0
            else ValidationVerdict.INVALID
        )

    results["province_id"] = _check_int("province_id")
    results["city_id"] = _check_int("city_id")

    return results


# ── Province–City Consistency ──────────────────────────────────────────────

def rule_province_city_consistency(
    store: Store,
) -> dict[str, ValidationVerdict]:
    """
    [NOT IMPLEMENTED YET — PLACEHOLDER]
    Check that city_id belongs to the specified province_id.
    Currently returns UNKNOWN for both fields to avoid influencing the score.
    Future: integrate with GeoKB province/city mapping.
    """
    try:
        province = (
            int(store.province_id)
            if getattr(store, "province_id", None) is not None
            else None
        )
        city = (
            int(store.city_id)
            if getattr(store, "city_id", None) is not None
            else None
        )
    except (TypeError, ValueError):
        return {
            "province_id": ValidationVerdict.INVALID,
            "city_id": ValidationVerdict.INVALID,
        }

    if province is None or city is None:
        return {
            "province_id": ValidationVerdict.INVALID,
            "city_id": ValidationVerdict.INVALID,
        }

    # TODO: integrate with GeoKB province/city mapping.
    return {
        "province_id": ValidationVerdict.UNKNOWN,
        "city_id": ValidationVerdict.UNKNOWN,
    }


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║          R U L E   R E G I S T R Y   +   D I S C O V E R Y             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# Master registry — populated via discover().
VALIDITY_RULES: list[ValidityRule] = []


def discover() -> list[ValidityRule]:
    """
    Auto-discover all ValidityRule instances defined in this module.

    Scans the module's global namespace for ValidityRule objects and
    returns them sorted by priority. This means adding a new rule is as
    simple as creating a ValidityRule at module level — no manual
    registration needed.

    Called once at import time; result is cached in VALIDITY_RULES.
    """
    global VALIDITY_RULES

    if VALIDITY_RULES:
        return VALIDITY_RULES

    frame = inspect.currentframe()

    try:
        module_globals = frame.f_back.f_globals if frame.f_back else {}
    finally:
        del frame

    rules: list[ValidityRule] = []

    for obj in module_globals.values():
        if isinstance(obj, ValidityRule):
            rules.append(obj)

    rules.sort(key=lambda r: r.priority)
    VALIDITY_RULES = rules

    return VALIDITY_RULES


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║     R U L E   D E F I N I T I O N S   (registered via discover)        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

RULE_IRAN_PHONE = ValidityRule(
    rule_name="iran_phone",
    description="Iranian landline (canonical_phone) + mobile pattern",
    priority=10,
    metadata={
        "locale": "IR",
        "format": "0XX-XXXXXXX",
        "mobile_format": "09XXXXXXXXX",
    },
    check=rule_iran_phone,
)

RULE_POSTAL_CODE = ValidityRule(
    rule_name="postal_code",
    description="10-digit Iranian postal code format",
    priority=10,
    metadata={"locale": "IR", "length": 10},
    check=rule_iran_postal_code,
)

RULE_COORDINATE_RANGE = ValidityRule(
    rule_name="coordinate_range",
    description="Latitude [-90,90], longitude [-180,180], non-zero",
    priority=5,
    metadata={
        "domain": "geo",
        "lat_range": [-90, 90],
        "lon_range": [-180, 180],
    },
    check=rule_coordinate_range,
)

RULE_COORDINATE_PRECISION = ValidityRule(
    rule_name="coordinate_precision",
    description=(
        "Decimal precision of lat/lon "
        "(≥5 = VALID, 3-4 = WARNING, <3 = INVALID)"
    ),
    priority=6,
    metadata={
        "domain": "geo",
        "min_precision": 5,
        "warn_precision": 3,
    },
    check=rule_coordinate_precision,
)

RULE_COORDINATE_IN_IRAN = ValidityRule(
    rule_name="coordinate_in_iran",
    description=(
        "Coordinates fall within rough Iran bounding box "
        "(24-40°N, 44-64°E)"
    ),
    priority=7,
    metadata={
        "domain": "geo",
        "bbox": {
            "lat": [24, 40],
            "lon": [44, 64],
        },
    },
    check=rule_coordinate_in_iran,
)

RULE_COORDINATE_SWAP = ValidityRule(
    rule_name="coordinate_swap_detection",
    description="Warn if lat/lon appear swapped",
    priority=8,
    metadata={
        "domain": "geo",
        "type": "heuristic",
    },
    check=rule_coordinate_swap_detection,
)

RULE_PROVINCE_CITY_ID = ValidityRule(
    rule_name="province_city_id_positive",
    description="Geo ID positivity: province_id/city_id > 0",
    priority=10,
    metadata={"domain": "address"},
    check=rule_province_city_id_positive,
)

RULE_PROVINCE_CITY_CONSISTENCY = ValidityRule(
    rule_name="province_city_consistency",
    description=(
        "[NOT IMPLEMENTED YET] city belongs to declared province "
        "(placeholder)"
    ),
    priority=50,
    metadata={
        "domain": "address",
        "status": "placeholder",
        "todo": "integrate GeoKB",
    },
    check=rule_province_city_consistency,
)


# ── Bootstrap discovery ────────────────────────────────────────────────────

discover()