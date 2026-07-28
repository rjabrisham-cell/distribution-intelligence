# ============================================================================
# Distribution Intelligence Platform (DIP)
# Sprint 2 — Data Quality Audit Engine
# Contract v1.2 (Frozen)
#
# Field Profile — Single Source of Truth for ALL audit dimensions
# ============================================================================

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                    V A L I D A T I O N   R E S U L T                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class ValidationVerdict(str, Enum):
    VALID   = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    UNKNOWN = "unknown"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       W E I G H T   T I E R S                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class WeightTier(IntEnum):
    CRITICAL  = 15
    IMPORTANT = 10
    STANDARD  = 5
    OPTIONAL  = 2


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                       F I E L D   G R O U P S                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class FieldGroup(str, Enum):
    IDENTITY   = "identity"
    CONTACT    = "contact"
    ADDRESS    = "address"
    COORDINATE = "coordinate"
    BUSINESS   = "business"


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║              V A L I D A T O R S   ( برون‌سپاری‌پذیر )                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
#
# هر Validator یک Callable با امضای (Any) -> ValidationVerdict است.
# در Sprint بعد به services/validators/ منتقل می‌شوند بدون کوچک‌ترین تغییر
# در FIELD_PROFILE.

def _not_empty(v: Any) -> ValidationVerdict:
    if v is None:
        return ValidationVerdict.INVALID
    return ValidationVerdict.VALID if str(v).strip() else ValidationVerdict.INVALID


def _min_len(n: int) -> Callable[[Any], ValidationVerdict]:
    def fn(v: Any) -> ValidationVerdict:
        if v is None:
            return ValidationVerdict.INVALID
        if not str(v).strip():
            return ValidationVerdict.INVALID
        return ValidationVerdict.VALID if len(str(v).strip()) >= n else ValidationVerdict.INVALID
    return fn


def _positive_id(v: Any) -> ValidationVerdict:
    """شناسه‌های عددی (province_id, city_id, ...) — باید > 0 باشند."""
    if v is None:
        return ValidationVerdict.INVALID
    try:
        n = int(v)
    except (TypeError, ValueError):
        return ValidationVerdict.INVALID
    return ValidationVerdict.VALID if n > 0 else ValidationVerdict.INVALID


def _optional_id(v: Any) -> ValidationVerdict:
    """region_id: >= 0 قابل قبول است (۰ یعنی ثبت نشده)."""
    if v is None:
        return ValidationVerdict.WARNING
    try:
        n = int(v)
    except (TypeError, ValueError):
        return ValidationVerdict.WARNING
    return ValidationVerdict.VALID if n >= 0 else ValidationVerdict.WARNING


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
    return ValidationVerdict.VALID if _IRAN_PHONE_RE.match(cleaned) else ValidationVerdict.WARNING


def _valid_mobile(v: Any) -> ValidationVerdict:
    """موبایل: یا ۰۹xxxxxxxxx یا خالی."""
    if v is None:
        return ValidationVerdict.WARNING  # ممکن است فروشگاه موبایل نداشته باشد
    s = str(v).strip().replace(" ", "")
    if s == "":
        return ValidationVerdict.WARNING
    return ValidationVerdict.VALID if re.match(r"^09\d{9}$", s) else ValidationVerdict.WARNING


def _valid_postal_code(v: Any) -> ValidationVerdict:
    if v is None:
        return ValidationVerdict.WARNING
    s = str(v).strip()
    if s == "":
        return ValidationVerdict.WARNING
    return ValidationVerdict.VALID if re.match(r"^\d{10}$", s) else ValidationVerdict.WARNING


def _valid_address(v: Any) -> ValidationVerdict:
    """آدرس متنی: حداقل ۱۰ کاراکتر."""
    if v is None:
        return ValidationVerdict.INVALID
    s = str(v).strip()
    if not s:
        return ValidationVerdict.INVALID
    return ValidationVerdict.VALID if len(s) >= 10 else ValidationVerdict.WARNING


def _valid_credit(v: Any) -> ValidationVerdict:
    """credit: ۰ یا ۱ — فیلد اختیاری تجاری."""
    if v is None:
        return ValidationVerdict.UNKNOWN
    try:
        n = int(v)
    except (TypeError, ValueError):
        return ValidationVerdict.UNKNOWN
    return ValidationVerdict.VALID if n in (0, 1) else ValidationVerdict.WARNING


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║              F I E L D   P R O F I L E   (Single Source of Truth)        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

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
# تعریف تمام فیلدهای مدل واقعی Store — بدون حتی یک فیلد فرضی
# ═══════════════════════════════════════════════════════════════════════════
# fmt: off
FIELD_PROFILE: dict[str, FieldProfile] = {
    # ═══════════════  IDENTITY  ═══════════════
    "shop_name":    FieldProfile("shop_name",    FieldGroup.IDENTITY,   WeightTier.CRITICAL,  True,  "نام فروشگاه",       _min_len(2)),
    "manager_name": FieldProfile("manager_name", FieldGroup.IDENTITY,   WeightTier.OPTIONAL,  False, "نام مدیر",           _not_empty),

    # ═══════════════  CONTACT   ═══════════════
    "mobile":       FieldProfile("mobile",       FieldGroup.CONTACT,    WeightTier.IMPORTANT, False, "شماره موبایل",       _valid_mobile),
    "phone":        FieldProfile("phone",        FieldGroup.CONTACT,    WeightTier.IMPORTANT, False, "شماره ثابت",         _valid_iran_phone),

    # ═══════════════  ADDRESS   ═══════════════
    "province_id":  FieldProfile("province_id",  FieldGroup.ADDRESS,    WeightTier.CRITICAL,  True,  "استان",             _positive_id),
    "city_id":      FieldProfile("city_id",      FieldGroup.ADDRESS,    WeightTier.CRITICAL,  True,  "شهر",               _positive_id),
    "region_id":    FieldProfile("region_id",    FieldGroup.ADDRESS,    WeightTier.STANDARD,  False, "منطقه",             _optional_id),
    "address":      FieldProfile("address",      FieldGroup.ADDRESS,    WeightTier.CRITICAL,  True,  "آدرس متنی",         _valid_address),
    "plaque":       FieldProfile("plaque",       FieldGroup.ADDRESS,    WeightTier.OPTIONAL,  False, "پلاک",              _not_empty),
    "unit":         FieldProfile("unit",         FieldGroup.ADDRESS,    WeightTier.OPTIONAL,  False, "واحد",              _not_empty),
    "floor":        FieldProfile("floor",        FieldGroup.ADDRESS,    WeightTier.OPTIONAL,  False, "طبقه",              _not_empty),
    "postal_code":  FieldProfile("postal_code",  FieldGroup.ADDRESS,    WeightTier.STANDARD,  False, "کد پستی",           _valid_postal_code),

    # ═══════════════  COORDINATE  ═══════════
    "latitude":     FieldProfile("latitude",     FieldGroup.COORDINATE, WeightTier.CRITICAL,  True,  "عرض جغرافیایی",     _valid_lat),
    "longitude":    FieldProfile("longitude",    FieldGroup.COORDINATE, WeightTier.CRITICAL,  True,  "طول جغرافیایی",     _valid_lon),

    # ═══════════════  BUSINESS   ═══════════════
    "credit":       FieldProfile("credit",       FieldGroup.BUSINESS,   WeightTier.OPTIONAL,  False, "وضعیت اعتبار",      _valid_credit),
}
# fmt: on


# ── Derived (computed once) ────────────────────────────────────────────────
_REQUIRED_FIELDS: tuple[str, ...] = tuple(f for f, p in FIELD_PROFILE.items() if p.required)
_TOTAL_WEIGHT: int = sum(p.weight for p in FIELD_PROFILE.values())

_GROUP_WEIGHTS: dict[FieldGroup, int] = {}
for _p in FIELD_PROFILE.values():
    _GROUP_WEIGHTS[_p.group] = _GROUP_WEIGHTS.get(_p.group, 0) + _p.weight

assert _TOTAL_WEIGHT > 0, "FIELD_PROFILE is empty — total weight is zero"


def get_profile(field_name: str) -> FieldProfile | None:
    return FIELD_PROFILE.get(field_name)
