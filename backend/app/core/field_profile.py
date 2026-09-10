# ============================================================================
# Distribution Intelligence Platform (DIP)
# Sprint 2 — Data Quality Audit Engine
# Contract v2.0 (Frozen — three-tier weight contract)
#
# Field Profile — Single Source of Truth for ALL audit dimensions
# ============================================================================

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, Callable


class ValidationVerdict(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    UNKNOWN = "unknown"


class WeightTier(IntEnum):
    CRITICAL = 15
    IMPORTANT = 10
    OPTIONAL = 2


class FieldGroup(str, Enum):
    IDENTITY = "identity"
    CONTACT = "contact"
    ADDRESS = "address"
    COORDINATE = "coordinate"


def _not_empty(v: Any) -> ValidationVerdict:
    if v is None:
        return ValidationVerdict.INVALID
    return (
        ValidationVerdict.VALID
        if str(v).strip()
        else ValidationVerdict.INVALID
    )


def _min_len(n: int) -> Callable[[Any], ValidationVerdict]:
    def fn(v: Any) -> ValidationVerdict:
        if v is None:
            return ValidationVerdict.INVALID
        if not str(v).strip():
            return ValidationVerdict.INVALID
        return (
            ValidationVerdict.VALID
            if len(str(v).strip()) >= n
            else ValidationVerdict.INVALID
        )

    return fn


def _positive_id(v: Any) -> ValidationVerdict:
    """شناسه‌های عددی اجباری (province_id, city_id) — باید > 0 باشند."""
    if v is None:
        return ValidationVerdict.INVALID

    try:
        n = int(v)
    except (TypeError, ValueError):
        return ValidationVerdict.INVALID

    return ValidationVerdict.VALID if n > 0 else ValidationVerdict.INVALID


def _valid_lat(v: Any) -> ValidationVerdict:
    if v is None:
        return ValidationVerdict.INVALID

    try:
        f = float(v)
    except (TypeError, ValueError):
        return ValidationVerdict.INVALID

    if abs(f) <= 0.000_001:
        return ValidationVerdict.INVALID

    if not (-90.0 <= f <= 90.0):
        return ValidationVerdict.INVALID

    return ValidationVerdict.VALID


def _valid_lon(v: Any) -> ValidationVerdict:
    if v is None:
        return ValidationVerdict.INVALID

    try:
        f = float(v)
    except (TypeError, ValueError):
        return ValidationVerdict.INVALID

    if abs(f) <= 0.000_001:
        return ValidationVerdict.INVALID

    if not (-180.0 <= f <= 180.0):
        return ValidationVerdict.INVALID

    return ValidationVerdict.VALID


_IRAN_PHONE_RE = re.compile(r"^(0\d{2,3}-?\d{7,8}|09\d{9})$")


def _valid_iran_phone(v: Any) -> ValidationVerdict:
    if v is None:
        return ValidationVerdict.INVALID

    cleaned = str(v).strip().replace(" ", "")

    if not cleaned:
        return ValidationVerdict.INVALID

    return (
        ValidationVerdict.VALID
        if _IRAN_PHONE_RE.match(cleaned)
        else ValidationVerdict.WARNING
    )


def _valid_mobile(v: Any) -> ValidationVerdict:
    """موبایل: یا ۰۹xxxxxxxxx یا خالی — خالی بودن مسدودکننده نیست
    (یک فروشگاه ممکن است فقط تلفن ثابت داشته باشد)."""
    if v is None:
        return ValidationVerdict.WARNING

    s = str(v).strip().replace(" ", "")

    if s == "":
        return ValidationVerdict.WARNING

    return (
        ValidationVerdict.VALID
        if re.match(r"^09\d{9}$", s)
        else ValidationVerdict.WARNING
    )


def _valid_postal_code(v: Any) -> ValidationVerdict:
    if v is None:
        return ValidationVerdict.WARNING

    s = str(v).strip()

    if s == "":
        return ValidationVerdict.WARNING

    return (
        ValidationVerdict.VALID
        if re.match(r"^\d{10}$", s)
        else ValidationVerdict.WARNING
    )


def _valid_address(v: Any) -> ValidationVerdict:
    """آدرس متنی: حداقل ۱۰ کاراکتر."""
    if v is None:
        return ValidationVerdict.INVALID

    s = str(v).strip()

    if not s:
        return ValidationVerdict.INVALID

    return (
        ValidationVerdict.VALID
        if len(s) >= 10
        else ValidationVerdict.WARNING
    )


@dataclass(frozen=True, slots=True)
class FieldProfile:
    field_name: str
    group: FieldGroup
    weight: int
    required: bool
    label_fa: str
    validator: Callable[[Any], ValidationVerdict]

    def validate(self, value: Any) -> ValidationVerdict:
        return self.validator(value)


# ═══════════════════════════════════════════════════════════════════════════
# تعریف تمام فیلدهای مدل واقعی Store — مطابق ستون‌های app/models/store.py
# بدون حتی یک فیلد فرضی. قرارداد ۳ سطحی: Critical / Important / Optional
#
#   Critical   = مسدودکنندهٔ Readiness (weight 15)
#   Important  = تأثیرگذار ولی غیرمسدودکننده (weight 10)
#   Optional   = اطلاع‌رسانی (weight 2)
#
# NOTE (MVP scope): county_id / district_id / neighborhood_id / village_id
# و نام‌های متنی متناظرشان از MVP خارج شده‌اند — فقط جغرافیای پایه
# (province_id / city_id) حفظ می‌شود.
# ═══════════════════════════════════════════════════════════════════════════

# fmt: off
FIELD_PROFILE: dict[str, FieldProfile] = {
    # IDENTITY
    "canonical_name": FieldProfile(
        "canonical_name",
        FieldGroup.IDENTITY,
        WeightTier.CRITICAL,
        True,
        "نام فروشگاه",
        _not_empty,
    ),
    "manager_name": FieldProfile(
        "manager_name",
        FieldGroup.IDENTITY,
        WeightTier.IMPORTANT,
        False,
        "نام مدیر",
        _not_empty,
    ),

    # CONTACT
    "canonical_phone": FieldProfile(
        "canonical_phone",
        FieldGroup.CONTACT,
        WeightTier.CRITICAL,
        False,
        "شماره ثابت",
        _valid_iran_phone,
    ),
    "mobile": FieldProfile(
        "mobile",
        FieldGroup.CONTACT,
        WeightTier.CRITICAL,
        False,
        "شماره موبایل",
        _valid_mobile,
    ),

    # ADDRESS
    "province_id": FieldProfile(
        "province_id",
        FieldGroup.ADDRESS,
        WeightTier.CRITICAL,
        True,
        "استان",
        _positive_id,
    ),
    "city_id": FieldProfile(
        "city_id",
        FieldGroup.ADDRESS,
        WeightTier.CRITICAL,
        True,
        "شهر",
        _positive_id,
    ),
    "address": FieldProfile(
        "address",
        FieldGroup.ADDRESS,
        WeightTier.CRITICAL,
        True,
        "آدرس متنی",
        _valid_address,
    ),
    "postal_code": FieldProfile(
        "postal_code",
        FieldGroup.ADDRESS,
        WeightTier.IMPORTANT,
        False,
        "کد پستی",
        _valid_postal_code,
    ),
    "plaque": FieldProfile(
        "plaque",
        FieldGroup.ADDRESS,
        WeightTier.OPTIONAL,
        False,
        "پلاک",
        _not_empty,
    ),
    "unit": FieldProfile(
        "unit",
        FieldGroup.ADDRESS,
        WeightTier.OPTIONAL,
        False,
        "واحد",
        _not_empty,
    ),
    "floor": FieldProfile(
        "floor",
        FieldGroup.ADDRESS,
        WeightTier.OPTIONAL,
        False,
        "طبقه",
        _not_empty,
    ),

    # COORDINATE
    "latitude": FieldProfile(
        "latitude",
        FieldGroup.COORDINATE,
        WeightTier.CRITICAL,
        True,
        "عرض جغرافیایی",
        _valid_lat,
    ),
    "longitude": FieldProfile(
        "longitude",
        FieldGroup.COORDINATE,
        WeightTier.CRITICAL,
        True,
        "طول جغرافیایی",
        _valid_lon,
    ),
}
# fmt: on


# ── Derived (computed once) ────────────────────────────────────────────────

_REQUIRED_FIELDS: tuple[str, ...] = tuple(
    field_name
    for field_name, profile in FIELD_PROFILE.items()
    if profile.required
)

_TOTAL_WEIGHT: int = sum(
    profile.weight
    for profile in FIELD_PROFILE.values()
)

_GROUP_WEIGHTS: dict[FieldGroup, int] = {}

for _profile in FIELD_PROFILE.values():
    _GROUP_WEIGHTS[_profile.group] = (
        _GROUP_WEIGHTS.get(_profile.group, 0)
        + _profile.weight
    )

assert _TOTAL_WEIGHT > 0, "FIELD_PROFILE is empty — total weight is zero"


def get_profile(field_name: str) -> FieldProfile | None:
    return FIELD_PROFILE.get(field_name)