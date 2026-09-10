"""
DIP Matching Engine — Pure Utility Functions

This module contains deterministic, side-effect-free helper functions used by
the Matching subsystem.

Responsibilities
----------------
- Persian / Arabic digit normalization
- conservative Persian / Arabic text normalization
- phone normalization
- tokenization
- Haversine geographic distance
- spatial-grid key generation
- neighboring spatial-grid key generation
- stable integer de-duplication

Non-responsibilities
--------------------
- ORM / SQLAlchemy access
- database access
- persistence
- candidate retrieval
- matching decisions
- Master Store modification
- store_code interpretation

Important
---------
These functions are deliberately conservative.

Raw business data must remain unchanged in the database. Normalized values
produced here are search / matching representations only.

No hard-coded Tehran phone prefix is used. A landline area code must be
provided explicitly by the caller when required.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable


# ============================================================================
# Character translation
# ============================================================================


_DIGIT_TRANSLATION = str.maketrans(
    {
        # Persian digits
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",

        # Arabic-Indic digits
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)


_PERSIAN_CHARACTER_TRANSLATION = str.maketrans(
    {
        # Arabic Yeh -> Persian Yeh
        "ي": "ی",
        "ى": "ی",
        "ئ": "ی",

        # Arabic Kaf -> Persian Kaf
        "ك": "ک",

        # Common Heh variants
        "ۀ": "ه",
        "ة": "ه",
        "ە": "ه",

        # Alef variants
        "أ": "ا",
        "إ": "ا",
        "ٱ": "ا",

        # Waw with hamza
        "ؤ": "و",

        # Tatweel
        "ـ": "",

        # Zero-width characters -> normal space
        "\u200c": " ",  # ZWNJ
        "\u200d": " ",  # ZWJ
        "\u200e": " ",  # LRM
        "\u200f": " ",  # RLM
        "\ufeff": " ",  # BOM / zero-width no-break space
    }
)


_WHITESPACE_RE = re.compile(
    r"\s+",
    flags=re.UNICODE,
)

_NON_PHONE_DIGIT_RE = re.compile(
    r"\D+",
    flags=re.UNICODE,
)


# ============================================================================
# Digit normalization
# ============================================================================


def normalize_digits(
    value: object,
) -> str:
    """
    Convert Persian and Arabic-Indic digits to ASCII digits.

    Examples
    --------
    ۱۲۳ -> 123
    ١٢٣ -> 123

    None produces an empty string.
    """

    if value is None:
        return ""

    text = str(value)

    return text.translate(
        _DIGIT_TRANSLATION
    )


# ============================================================================
# Unicode helpers
# ============================================================================


def _remove_combining_marks(
    value: str,
) -> str:
    """
    Remove Unicode combining marks such as Arabic/Persian diacritics.
    """

    return "".join(
        character
        for character in value
        if not unicodedata.combining(
            character
        )
    )


def _replace_punctuation_with_spaces(
    value: str,
) -> str:
    """
    Replace punctuation and symbol characters with spaces.

    Letters, numbers and whitespace are preserved.

    This is intentionally conservative: punctuation is not concatenated away,
    because concatenation could incorrectly merge separate address/name tokens.
    """

    output: list[str] = []

    for character in value:
        category = unicodedata.category(
            character
        )

        if (
            category.startswith("P")
            or category.startswith("S")
        ):
            output.append(" ")
        else:
            output.append(
                character
            )

    return "".join(
        output
    )


# ============================================================================
# Text normalization
# ============================================================================


def normalize_text(
    value: object,
) -> str:
    """
    Normalize text for Matching retrieval/scoring.

    Operations
    ----------
    1. convert value to string
    2. normalize Persian/Arabic digits
    3. Unicode NFKC normalization
    4. normalize common Arabic/Persian character variants
    5. remove combining marks / diacritics
    6. replace punctuation/symbols with spaces
    7. collapse whitespace
    8. casefold

    Important
    ---------
    This function does NOT remove business suffixes or aggressively rewrite
    store names. Such behavior could change Matching recall/precision and is
    outside the behavior-preserving refactor.

    Examples
    --------
    فروشگاه كيان ۱۲۳
        -> فروشگاه کیان 123
    """

    if value is None:
        return ""

    text = normalize_digits(
        value
    )

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = text.translate(
        _PERSIAN_CHARACTER_TRANSLATION
    )

    # NFKD makes combining marks explicit so they can be removed.
    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = _remove_combining_marks(
        text
    )

    # Re-compose after diacritic removal.
    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = _replace_punctuation_with_spaces(
        text
    )

    text = _WHITESPACE_RE.sub(
        " ",
        text,
    ).strip()

    return text.casefold()


# ============================================================================
# Phone normalization
# ============================================================================


def _normalize_area_code(
    area_code: object,
) -> str:
    """
    Normalize a supplied Iranian landline area code.

    Examples
    --------
    021  -> 021
    21   -> 021
    +9821 -> 021

    No area code is guessed.
    """

    if area_code is None:
        return ""

    digits = _NON_PHONE_DIGIT_RE.sub(
        "",
        normalize_digits(
            area_code
        ),
    )

    if not digits:
        return ""

    if digits.startswith("0098"):
        digits = digits[4:]

    elif digits.startswith("98"):
        digits = digits[2:]

    if not digits:
        return ""

    if not digits.startswith("0"):
        digits = (
            "0"
            + digits
        )

    return digits


def normalize_phone(
    value: object,
    area_code: str | None = None,
) -> str:
    """
    Normalize Iranian phone numbers conservatively.

    Behavior
    --------
    - Persian/Arabic digits -> ASCII
    - remove non-digit characters
    - 0098xxxxxxxxxx -> 0xxxxxxxxxx
    - 98xxxxxxxxxx   -> 0xxxxxxxxxx
    - mobile 9xxxxxxxxx -> 09xxxxxxxxx
    - 8-digit landline gets area code ONLY when area_code is explicitly given

    Important
    ---------
    No city prefix such as 021 is hard-coded.

    Missing/empty values return an empty string.

    Examples
    --------
    021-88776655 -> 02188776655
    +98 912 123 4567 -> 09121234567
    """

    if value is None:
        return ""

    digits = _NON_PHONE_DIGIT_RE.sub(
        "",
        normalize_digits(
            value
        ),
    )

    if not digits:
        return ""

    # --------------------------------------------------------------
    # International Iranian prefixes
    # --------------------------------------------------------------

    if digits.startswith("0098"):
        digits = digits[4:]

        if digits:
            digits = (
                "0"
                + digits.lstrip("0")
            )

    elif digits.startswith("98"):
        digits = digits[2:]

        if digits:
            digits = (
                "0"
                + digits.lstrip("0")
            )

    # --------------------------------------------------------------
    # Iranian mobile without leading zero
    # --------------------------------------------------------------

    if (
        len(digits) == 10
        and digits.startswith("9")
    ):
        digits = (
            "0"
            + digits
        )

    # --------------------------------------------------------------
    # Local 8-digit landline
    #
    # Only enrich it when the caller supplied the area code.
    # --------------------------------------------------------------

    if len(digits) == 8:
        normalized_area_code = (
            _normalize_area_code(
                area_code
            )
        )

        if normalized_area_code:
            digits = (
                normalized_area_code
                + digits
            )

    return digits


# ============================================================================
# Tokenization
# ============================================================================


def tokenize(
    value: object,
) -> tuple[str, ...]:
    """
    Tokenize normalized text into unique stable tokens.

    The original token order is preserved.

    Empty tokens are ignored.

    No business-specific stop-word removal occurs in this behavior-preserving
    phase.
    """

    normalized = normalize_text(
        value
    )

    if not normalized:
        return ()

    tokens: list[str] = []
    seen: set[str] = set()

    for token in normalized.split():
        token = token.strip()

        if not token:
            continue

        if token in seen:
            continue

        seen.add(
            token
        )

        tokens.append(
            token
        )

    return tuple(
        tokens
    )


# ============================================================================
# Geographic distance
# ============================================================================


def haversine_distance_meters(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculate great-circle distance between two WGS84 coordinates.

    Returns distance in meters.

    This is used only after spatial candidate retrieval. The Spatial Grid
    itself is a retrieval accelerator and does not replace exact Haversine
    distance scoring.
    """

    lat1 = math.radians(
        float(latitude_1)
    )

    lon1 = math.radians(
        float(longitude_1)
    )

    lat2 = math.radians(
        float(latitude_2)
    )

    lon2 = math.radians(
        float(longitude_2)
    )

    delta_lat = (
        lat2
        - lat1
    )

    delta_lon = (
        lon2
        - lon1
    )

    sin_lat = math.sin(
        delta_lat / 2.0
    )

    sin_lon = math.sin(
        delta_lon / 2.0
    )

    a = (
        sin_lat * sin_lat
        + math.cos(lat1)
        * math.cos(lat2)
        * sin_lon
        * sin_lon
    )

    # Floating-point protection.
    a = min(
        1.0,
        max(
            0.0,
            a,
        ),
    )

    c = (
        2.0
        * math.atan2(
            math.sqrt(a),
            math.sqrt(
                1.0 - a
            ),
        )
    )

    earth_radius_meters = (
        6_371_008.8
    )

    return (
        earth_radius_meters
        * c
    )


# ============================================================================
# Spatial Grid
# ============================================================================


def spatial_grid_key(
    latitude: float,
    longitude: float,
    grid_step: float,
) -> tuple[int, int]:
    """
    Convert a coordinate into a deterministic integer Spatial Grid key.

    Example
    -------
    latitude  = 35.7219
    longitude = 51.3347
    grid_step = 0.01

    result:
        (3572, 5133)

    Integer bins are used instead of rounded floating-point strings to avoid
    unstable boundary behavior.
    """

    if grid_step <= 0.0:
        raise ValueError(
            "grid_step must be greater than zero"
        )

    lat = float(
        latitude
    )

    lon = float(
        longitude
    )

    lat_bin = math.floor(
        lat / grid_step
    )

    lon_bin = math.floor(
        lon / grid_step
    )

    return (
        int(lat_bin),
        int(lon_bin),
    )


def neighboring_grid_keys(
    latitude: float,
    longitude: float,
    grid_step: float,
    *,
    radius: int = 1,
) -> list[tuple[int, int]]:
    """
    Return the base Spatial Grid cell and neighboring cells.

    Examples
    --------
    radius = 0
        1 cell

    radius = 1
        3 x 3 = 9 cells

    radius = 2
        5 x 5 = 25 cells

    The returned keys use the exact same integer-bin contract as
    spatial_grid_key().

    This function fixes the previous defect where undefined variables
    ``base_lat`` / ``base_lon`` were referenced instead of the actual grid
    bins returned by spatial_grid_key().
    """

    if radius < 0:
        raise ValueError(
            "radius must be >= 0"
        )

    base_lat_bin, base_lon_bin = (
        spatial_grid_key(
            latitude,
            longitude,
            grid_step,
        )
    )

    keys: list[
        tuple[int, int]
    ] = []

    for lat_offset in range(
        -radius,
        radius + 1,
    ):
        for lon_offset in range(
            -radius,
            radius + 1,
        ):
            keys.append(
                (
                    base_lat_bin
                    + lat_offset,

                    base_lon_bin
                    + lon_offset,
                )
            )

    return keys


# ============================================================================
# Stable de-duplication
# ============================================================================


def unique_ints(
    values: Iterable[int],
) -> list[int]:
    """
    Remove duplicate integer IDs while preserving their first-seen order.

    This is used when exact, spatial and token retrieval paths return the same
    Master Store through multiple evidence channels.
    """

    result: list[int] = []
    seen: set[int] = set()

    for raw_value in values:
        if raw_value is None:
            continue

        try:
            value = int(
                raw_value
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if value in seen:
            continue

        seen.add(
            value
        )

        result.append(
            value
        )

    return result


# ============================================================================
# Public API
# ============================================================================


__all__ = [
    "normalize_digits",
    "normalize_text",
    "normalize_phone",
    "tokenize",
    "haversine_distance_meters",
    "spatial_grid_key",
    "neighboring_grid_keys",
    "unique_ints",
]