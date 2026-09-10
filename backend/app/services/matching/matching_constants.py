"""
DIP Matching Engine — Frozen Constants

This module contains constants shared by the Matching subsystem.

IMPORTANT
---------
Phase 1 is a behavior-preserving refactor.

Do not change thresholds, scoring weights, or safety-gate values here
unless a later Matching calibration phase explicitly approves the change.

Current production/baseline contract:

    PRECISE threshold   = 0.90
    SUGGESTED threshold = 0.72
    decision margin     = 0.08

Scoring weights:

    coordinates = 0.40
    name        = 0.30
    phone       = 0.20
    address     = 0.10
"""

from __future__ import annotations

from typing import Final


# ============================================================================
# Decision thresholds — FROZEN
# ============================================================================

PRECISE_THRESHOLD: Final[float] = 0.90
SUGGESTED_THRESHOLD: Final[float] = 0.72
MIN_DECISION_MARGIN: Final[float] = 0.08


# ============================================================================
# Scoring weights — FROZEN
# ============================================================================

COORDINATE_WEIGHT: Final[float] = 0.40
NAME_WEIGHT: Final[float] = 0.30
PHONE_WEIGHT: Final[float] = 0.20
ADDRESS_WEIGHT: Final[float] = 0.10

TOTAL_WEIGHT: Final[float] = (
    COORDINATE_WEIGHT
    + NAME_WEIGHT
    + PHONE_WEIGHT
    + ADDRESS_WEIGHT
)


# ============================================================================
# PRECISE safety-gate values — FROZEN
# ============================================================================

# geo + name
PRECISE_GEO_DISTANCE_METERS: Final[float] = 80.0
PRECISE_GEO_NAME_MIN_SCORE: Final[float] = 0.82

# name + address
PRECISE_NAME_ADDRESS_NAME_MIN_SCORE: Final[float] = 0.96
PRECISE_NAME_ADDRESS_ADDRESS_MIN_SCORE: Final[float] = 0.90


# ============================================================================
# Spatial retrieval
# ============================================================================
#
# These constants support the new in-memory spatial index.
#
# They do NOT alter scoring or decision thresholds.
#
# GRID_STEP_DEGREES = 0.01 is approximately 1.1 km north/south.
# Longitude distance varies with latitude.
#
# Neighbor radius = 2 means a 5x5 cell search when required.
# The final distance check must still use an exact distance function.
# ============================================================================

GRID_STEP_DEGREES: Final[float] = 0.01
GRID_NEIGHBOR_RADIUS: Final[int] = 2


# ============================================================================
# Retrieval limits
# ============================================================================

# Existing token fallback ceiling.
# Keep frozen during the behavior-preserving refactor.
MAX_TOKEN_POOL: Final[int] = 600


# ============================================================================
# Match method labels
# ============================================================================
#
# These are persistence/report labels, not domain enums.
# MatchStatus itself remains owned by app.core.enums.
# ============================================================================

MATCH_METHOD_EXISTING_MASTER_LINK: Final[str] = "existing_master_link"

MATCH_METHOD_NO_CANDIDATE_POOL: Final[str] = "no_candidate_pool"
MATCH_METHOD_GEO_UNRESOLVED: Final[str] = "geo_unresolved"

MATCH_METHOD_PRECISE_PREFIX: Final[str] = "precise"
MATCH_METHOD_SUGGESTED_PREFIX: Final[str] = "suggested"
MATCH_METHOD_UNRESOLVED_PREFIX: Final[str] = "unresolved"


# ============================================================================
# Evidence labels
# ============================================================================

EVIDENCE_GEO: Final[str] = "geo"
EVIDENCE_NAME: Final[str] = "name"
EVIDENCE_PHONE: Final[str] = "phone"
EVIDENCE_ADDRESS: Final[str] = "addr"


# ============================================================================
# Validation guard
# ============================================================================

if abs(TOTAL_WEIGHT - 1.0) > 1e-9:
    raise RuntimeError(
        "Matching scoring weights must sum to 1.0. "
        f"Current total: {TOTAL_WEIGHT}"
    )