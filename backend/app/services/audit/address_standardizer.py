# app/services/audit/address_standardizer.py
"""Address/Text Standardizer for `Store` entities (Readiness Pipeline — Slice 1).

Scope (ONLY these):
  - Normalize the text fields of a Store.
  - Convert Persian/Arabic digits to ASCII.
  - Unify ي->ی and ك->ک.
  - Collapse whitespace and strip inert zero-width characters.
  - Produce an immutable before/after snapshot (changes, field_results, warnings).

Explicitly OUT of scope:
  - NO in-place mutation of the source Store.
  - NO database access (session/commit/flush/update/lookup).
  - NO geographical lookup or validation.
  - NO validity decisions (phone/postal/coordinate correctness).
  - NO duplicate grouping or duplicate key generation.
  - Coordinates pass through raw and untouched (owned by coordinate_validator).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Persian (U+06F0..U+06F9) and Arabic-Indic (U+0660..U+0669) digits -> ASCII.
_FA_DIGITS_TRANS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

# Characters carrying no semantic weight; dropped outright.
# NOTE: ZWNJ (U+200C) is deliberately excluded — it is meaningful in Persian.
_ZERO_WIDTH = frozenset(
    {
        "\u200b",  # zero-width space
        "\ufeff",  # BOM / zero-width no-break space
        "\u200e",  # left-to-right mark
        "\u200f",  # right-to-left mark
        "\u00ad",  # soft hyphen
    }
)

_TEXT_FIELDS: Tuple[str, ...] = (
    "canonical_name",
    "manager_name",
    "address",
    "province_name",
    "city_name",
)
_PHONE_FIELDS: Tuple[str, ...] = ("canonical_phone", "mobile")
_POSTAL_FIELDS: Tuple[str, ...] = ("postal_code",)

_ALL_NORMALIZED_FIELDS: Tuple[str, ...] = _TEXT_FIELDS + _PHONE_FIELDS + _POSTAL_FIELDS


# ---------------------------------------------------------------------------
# Normalization primitives (pure, side-effect free)
# ---------------------------------------------------------------------------

def _strip_zero_width(value: str) -> str:
    return "".join(ch for ch in value if ch not in _ZERO_WIDTH)


def _normalize_text(value: Any) -> Optional[str]:
    """Generic text normalization. Returns None when the result is empty."""
    if value is None:
        return None

    text = str(value)
    text = _strip_zero_width(text)

    # Unify before NFKC so Persian ي/ك are not folded to Arabic forms.
    text = text.replace("\u064a", "\u06cc")  # ي -> ی
    text = text.replace("\u0643", "\u06a9")  # ك -> ک

    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_FA_DIGITS_TRANS)
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def _normalize_phone(value: Any) -> Optional[str]:
    """Phone/mobile: digits plus an optional single leading '+'. None if empty."""
    if value is None:
        return None

    text = str(value)
    text = _strip_zero_width(text)
    text = text.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_FA_DIGITS_TRANS)

    had_plus = text.lstrip().startswith("+")
    digits = re.sub(r"\D", "", text)

    if not digits:
        return None

    return ("+" + digits) if had_plus else digits


def _normalize_postal(value: Any) -> Optional[str]:
    """Postal code (conservative): digits -> ASCII, whitespace collapsed, stripped.

    Internal separators (e.g. '-') are intentionally preserved because the
    exact postal-code contract is not yet finalized downstream.
    """
    if value is None:
        return None

    text = str(value)
    text = _strip_zero_width(text)
    text = text.translate(_FA_DIGITS_TRANS)
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


# ---------------------------------------------------------------------------
# Immutable result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldChange:
    """One before -> after change on a single field."""

    field: str
    before: Optional[str]
    after: Optional[str]


@dataclass(frozen=True)
class FieldResult:
    """Per-field status of one normalization pass."""

    field: str
    present: bool
    normalized: Optional[str]
    changed: bool


@dataclass(frozen=True)
class AddressStandardizationResult:
    """Immutable normalization snapshot for one Store."""

    store_id: Any

    normalized_name: Optional[str]
    normalized_manager: Optional[str]
    normalized_address: Optional[str]
    normalized_phone: Optional[str]
    normalized_mobile: Optional[str]
    normalized_postal: Optional[str]
    normalized_province_name: Optional[str]
    normalized_city_name: Optional[str]

    # Raw pass-through coordinates — deliberately untouched.
    latitude: Any
    longitude: Any

    changes: Tuple[FieldChange, ...]
    warnings: Tuple[str, ...]
    field_results: Tuple[FieldResult, ...]

    @property
    def changed_fields(self) -> Tuple[str, ...]:
        """Names of fields whose normalized value differs from the raw value."""
        return tuple(change.field for change in self.changes)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AddressStandardizer:
    """Stateless standardizer.

    Reads attributes with `getattr`/`dict.get`, so it works with ORM objects,
    plain objects, dataclasses and dicts alike. Never mutates the source.
    """

    def standardize(self, raw: Any) -> AddressStandardizationResult:
        def _get(name: str) -> Any:
            if isinstance(raw, dict):
                return raw.get(name)
            return getattr(raw, name, None)

        raw_vals = {name: _get(name) for name in _ALL_NORMALIZED_FIELDS}

        normalized = {
            "canonical_name": _normalize_text(raw_vals["canonical_name"]),
            "manager_name": _normalize_text(raw_vals["manager_name"]),
            "address": _normalize_text(raw_vals["address"]),
            "canonical_phone": _normalize_phone(raw_vals["canonical_phone"]),
            "mobile": _normalize_phone(raw_vals["mobile"]),
            "postal_code": _normalize_postal(raw_vals["postal_code"]),
            "province_name": _normalize_text(raw_vals["province_name"]),
            "city_name": _normalize_text(raw_vals["city_name"]),
        }

        changes: list[FieldChange] = []
        field_results: list[FieldResult] = []
        warnings: list[str] = []

        for name in _ALL_NORMALIZED_FIELDS:
            raw_val = raw_vals[name]
            norm_val = normalized[name]

            raw_str = None if raw_val is None else str(raw_val)
            norm_str = None if norm_val is None else str(norm_val)

            present = raw_val is not None
            changed = raw_str != norm_str

            field_results.append(
                FieldResult(
                    field=name,
                    present=present,
                    normalized=norm_val,
                    changed=changed,
                )
            )

            if changed:
                changes.append(
                    FieldChange(
                        field=name,
                        before=raw_str,
                        after=norm_str,
                    )
                )

            # A present value that becomes empty after normalization signals
            # whitespace/zero-width-only input — a downstream warning without
            # making any validity decision here.
            if present and raw_str not in (None, "") and norm_val is None:
                warnings.append(f"field '{name}' became empty after normalization")

        return AddressStandardizationResult(
            store_id=_get("id"),
            normalized_name=normalized["canonical_name"],
            normalized_manager=normalized["manager_name"],
            normalized_address=normalized["address"],
            normalized_phone=normalized["canonical_phone"],
            normalized_mobile=normalized["mobile"],
            normalized_postal=normalized["postal_code"],
            normalized_province_name=normalized["province_name"],
            normalized_city_name=normalized["city_name"],
            latitude=_get("latitude"),
            longitude=_get("longitude"),
            changes=tuple(changes),
            warnings=tuple(warnings),
            field_results=tuple(field_results),
        )
