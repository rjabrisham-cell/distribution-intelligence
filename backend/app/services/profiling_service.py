"""
Profiling Service.

Analyzes imported data to provide quality metrics, distribution statistics,
and actionable insights for logistics optimization.

Key features:
    - Store distribution analysis (clustering, coverage gaps)
    - Order pattern detection (temporal, geographic)
    - Fleet capacity/utilization profiling
    - GPS data quality and movement analysis
    - Data completeness scoring
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.schemas.import_schema import EntityTypeEnum


class ProfilingService:
    """
    Analyzes data quality and distribution patterns across imported entities.

    Usage:
        service = ProfilingService()
        report = service.profile_stores(stores_data)
    """

    # ── Configuration ──────────────────────────────────────────

    # Tehran city center (approximate, for distance calculations)
    TEHRAN_CENTER_LAT: Decimal = Decimal("35.6892")
    TEHRAN_CENTER_LON: Decimal = Decimal("51.3890")

    # Density analysis grid size (degrees)
    GRID_SIZE: Decimal = Decimal("0.01")  # ~1.1 km at Tehran latitude

    # ── Public API: Multi-entity profiling ─────────────────────

    def profile(
        self,
        entity_type: EntityTypeEnum,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a comprehensive profiling report for any entity type.

        Returns:
            dict with entity-specific profile metrics.
        """
        profilers = {
            EntityTypeEnum.STORE: self.profile_stores,
            EntityTypeEnum.ORDER: self.profile_orders,
            EntityTypeEnum.FLEET: self.profile_vehicles,
            EntityTypeEnum.DRIVER: self.profile_drivers,
            EntityTypeEnum.GPS: self.profile_gps_records,
        }

        profiler = profilers.get(entity_type)
        if profiler is None:
            raise ValueError(f"No profiler for entity type: {entity_type}")

        return profiler(rows)

    # ── Store profiling ────────────────────────────────────────

    def profile_stores(self, stores: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze store data for distribution patterns and data quality.

        Metrics:
            - Total stores
            - Stores with/without coordinates
            - Geographic distribution (by grid cell)
            - Category distribution
            - Status distribution
            - Average service time
            - Data completeness score
        """
        total = len(stores)
        if total == 0:
            return {"entity": "STORE", "total": 0, "message": "No store data to profile."}

        coords_present = 0
        coords_missing = 0
        categories: Counter[str] = Counter()
        statuses: Counter[str] = Counter()
        grid_counts: Counter[tuple[int, int]] = Counter()
        service_times: list[int] = []
        completeness_scores: list[float] = []

        for store in stores:
            # Coordinates
            lat = store.get("latitude")
            lon = store.get("longitude")
            if lat and lon:
                coords_present += 1
                try:
                    grid_key = self._to_grid(Decimal(str(lat)), Decimal(str(lon)))
                    grid_counts[grid_key] += 1
                except Exception:
                    pass
            else:
                coords_missing += 1

            # Category
            cat = store.get("category")
            if cat:
                categories[str(cat)] += 1

            # Status
            status = store.get("status", "unknown")
            statuses[str(status)] += 1

            # Service time
            st = store.get("service_time_min")
            if st is not None:
                try:
                    service_times.append(int(st))
                except (ValueError, TypeError):
                    pass

            # Completeness score
            completeness_scores.append(self._row_completeness(store))

        avg_service_time = (
            sum(service_times) / len(service_times) if service_times else None
        )
        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        # Top grid cells (highest store density)
        top_grids = grid_counts.most_common(10)
        top_locations = [
            {
                "grid": f"{g[0]},{g[1]}",
                "approx_lat": float(g[0]) * float(self.GRID_SIZE) + float(self.TEHRAN_CENTER_LAT),
                "approx_lon": float(g[1]) * float(self.GRID_SIZE) + float(self.TEHRAN_CENTER_LON),
                "count": c,
            }
            for g, c in top_grids
        ]

        return {
            "entity": "STORE",
            "total": total,
            "coordinates": {
                "present": coords_present,
                "missing": coords_missing,
                "coverage_pct": round(coords_present / total * 100, 1),
            },
            "categories": dict(categories.most_common()),
            "status_distribution": dict(statuses),
            "service_time": {
                "avg_minutes": round(avg_service_time, 1) if avg_service_time else None,
                "min": min(service_times) if service_times else None,
                "max": max(service_times) if service_times else None,
            },
            "density": {
                "unique_grids": len(grid_counts),
                "max_grid_count": max(grid_counts.values()) if grid_counts else 0,
                "top_clusters": top_locations,
            },
            "data_quality": {
                "avg_completeness_pct": round(avg_completeness, 1),
                "rows_with_coords_pct": round(coords_present / total * 100, 1),
            },
        }

    # ── Order profiling ────────────────────────────────────────

    def profile_orders(self, orders: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze order data for delivery patterns.

        Metrics:
            - Total orders
            - Orders with coordinates
            - Weight/volume statistics
            - Temporal distribution (day of week, time windows)
            - Unique stores served
        """
        total = len(orders)
        if total == 0:
            return {"entity": "ORDER", "total": 0, "message": "No order data to profile."}

        weights: list[float] = []
        volumes: list[float] = []
        item_counts: list[int] = []
        store_codes: set[str] = set()
        statuses: Counter[str] = Counter()
        coord_count = 0
        completeness_scores: list[float] = []

        for order in orders:
            # Weight
            w = order.get("weight_kg")
            if w is not None:
                try:
                    weights.append(float(w))
                except (ValueError, TypeError):
                    pass

            # Volume
            v = order.get("volume_m3")
            if v is not None:
                try:
                    volumes.append(float(v))
                except (ValueError, TypeError):
                    pass

            # Items
            ic = order.get("item_count")
            if ic is not None:
                try:
                    item_counts.append(int(ic))
                except (ValueError, TypeError):
                    pass

            # Store
            sc = order.get("store_code")
            if sc:
                store_codes.add(str(sc))

            # Status
            statuses[str(order.get("status", "unknown"))] += 1

            # Coordinates
            if order.get("latitude") and order.get("longitude"):
                coord_count += 1

            # Completeness
            completeness_scores.append(self._row_completeness(order))

        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        return {
            "entity": "ORDER",
            "total": total,
            "unique_stores": len(store_codes),
            "orders_per_store": round(total / len(store_codes), 1) if store_codes else 0,
            "weight_kg": {
                "avg": round(sum(weights) / len(weights), 2) if weights else None,
                "min": round(min(weights), 2) if weights else None,
                "max": round(max(weights), 2) if weights else None,
                "total": round(sum(weights), 2) if weights else 0,
            },
            "volume_m3": {
                "avg": round(sum(volumes) / len(volumes), 3) if volumes else None,
                "total": round(sum(volumes), 3) if volumes else 0,
            },
            "items": {
                "avg": round(sum(item_counts) / len(item_counts), 1) if item_counts else None,
                "total": sum(item_counts) if item_counts else 0,
            },
            "coordinates_coverage_pct": round(coord_count / total * 100, 1),
            "status_distribution": dict(statuses),
            "data_quality": {
                "avg_completeness_pct": round(avg_completeness, 1),
            },
        }

    # ── Vehicle profiling ──────────────────────────────────────

    def profile_vehicles(self, vehicles: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze fleet data for capacity and utilization.

        Metrics:
            - Total vehicles
            - Type distribution
            - Capacity statistics
            - Cost statistics
            - Availability coverage
        """
        total = len(vehicles)
        if total == 0:
            return {"entity": "FLEET", "total": 0, "message": "No vehicle data to profile."}

        types: Counter[str] = Counter()
        capacities: list[float] = []
        volumes: list[float] = []
        cost_per_km: list[float] = []
        fixed_costs: list[float] = []
        statuses: Counter[str] = Counter()
        coord_count = 0
        completeness_scores: list[float] = []

        for v in vehicles:
            # Type
            vt = v.get("vehicle_type")
            if vt:
                types[str(vt)] += 1

            # Capacity
            cap = v.get("capacity_kg")
            if cap is not None:
                try:
                    capacities.append(float(cap))
                except (ValueError, TypeError):
                    pass

            # Volume
            vol = v.get("volume_m3")
            if vol is not None:
                try:
                    volumes.append(float(vol))
                except (ValueError, TypeError):
                    pass

            # Costs
            cpk = v.get("cost_per_km")
            if cpk is not None:
                try:
                    cost_per_km.append(float(cpk))
                except (ValueError, TypeError):
                    pass

            fc = v.get("fixed_cost")
            if fc is not None:
                try:
                    fixed_costs.append(float(fc))
                except (ValueError, TypeError):
                    pass

            # Status
            statuses[str(v.get("status", "unknown"))] += 1

            # Coordinates
            if v.get("latitude") and v.get("longitude"):
                coord_count += 1

            completeness_scores.append(self._row_completeness(v))

        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        return {
            "entity": "FLEET",
            "total": total,
            "type_distribution": dict(types),
            "capacity_kg": {
                "avg": round(sum(capacities) / len(capacities), 1) if capacities else None,
                "min": round(min(capacities), 1) if capacities else None,
                "max": round(max(capacities), 1) if capacities else None,
                "total": round(sum(capacities), 1) if capacities else 0,
            },
            "volume_m3": {
                "total": round(sum(volumes), 1) if volumes else 0,
            },
            "costs": {
                "avg_cost_per_km": round(sum(cost_per_km) / len(cost_per_km), 2) if cost_per_km else None,
                "avg_fixed_cost": round(sum(fixed_costs) / len(fixed_costs), 2) if fixed_costs else None,
            },
            "coordinates_coverage_pct": round(coord_count / total * 100, 1),
            "status_distribution": dict(statuses),
            "data_quality": {
                "avg_completeness_pct": round(avg_completeness, 1),
            },
        }

    # ── Driver profiling ───────────────────────────────────────

    def profile_drivers(self, drivers: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze driver data.

        Metrics:
            - Total drivers
            - Status distribution
            - License expiry status
            - Coordinate coverage
            - Data completeness
        """
        total = len(drivers)
        if total == 0:
            return {"entity": "DRIVER", "total": 0, "message": "No driver data to profile."}

        statuses: Counter[str] = Counter()
        expired_licenses = 0
        valid_licenses = 0
        coord_count = 0
        completeness_scores: list[float] = []

        now = datetime.utcnow()

        for d in drivers:
            statuses[str(d.get("status", "unknown"))] += 1

            # License expiry
            expiry = d.get("license_expiry")
            if expiry:
                try:
                    if isinstance(expiry, str):
                        expiry_date = datetime.fromisoformat(expiry)
                    else:
                        expiry_date = expiry
                    if expiry_date < now:
                        expired_licenses += 1
                    else:
                        valid_licenses += 1
                except (ValueError, TypeError):
                    pass

            # Coordinates
            if d.get("latitude") and d.get("longitude"):
                coord_count += 1

            completeness_scores.append(self._row_completeness(d))

        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        return {
            "entity": "DRIVER",
            "total": total,
            "status_distribution": dict(statuses),
            "licenses": {
                "valid": valid_licenses,
                "expired": expired_licenses,
                "unknown": total - valid_licenses - expired_licenses,
                "expired_pct": round(expired_licenses / total * 100, 1) if total else 0,
            },
            "coordinates_coverage_pct": round(coord_count / total * 100, 1),
            "data_quality": {
                "avg_completeness_pct": round(avg_completeness, 1),
            },
        }

    # ── GPS profiling ──────────────────────────────────────────

    def profile_gps_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze GPS data for quality and movement patterns.

        Metrics:
            - Total records
            - Unique vehicles
            - Time range
            - Speed statistics
            - Accuracy statistics
            - Data completeness
        """
        total = len(records)
        if total == 0:
            return {"entity": "GPS", "total": 0, "message": "No GPS data to profile."}

        plates: set[str] = set()
        speeds: list[float] = []
        accuracies: list[float] = []
        headings: list[float] = []
        timestamps: list[datetime] = []
        completeness_scores: list[float] = []

        high_accuracy = 0  # accuracy < 10m
        moving = 0          # speed > 5 km/h

        for rec in records:
            plate = rec.get("vehicle_plate")
            if plate:
                plates.add(str(plate))

            # Speed
            s = rec.get("speed_kmh")
            if s is not None:
                try:
                    speed_f = float(s)
                    speeds.append(speed_f)
                    if speed_f > 5:
                        moving += 1
                except (ValueError, TypeError):
                    pass

            # Accuracy
            a = rec.get("accuracy_m")
            if a is not None:
                try:
                    acc_f = float(a)
                    accuracies.append(acc_f)
                    if acc_f < 10:
                        high_accuracy += 1
                except (ValueError, TypeError):
                    pass

            # Heading
            h = rec.get("heading")
            if h is not None:
                try:
                    headings.append(float(h))
                except (ValueError, TypeError):
                    pass

            # Timestamp
            ts = rec.get("timestamp")
            if ts:
                try:
                    if isinstance(ts, str):
                        timestamps.append(datetime.fromisoformat(ts))
                    else:
                        timestamps.append(ts)
                except (ValueError, TypeError):
                    pass

            completeness_scores.append(self._row_completeness(rec))

        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        # Time range
        time_range_start = min(timestamps) if timestamps else None
        time_range_end = max(timestamps) if timestamps else None
        time_span_hours = (
            (time_range_end - time_range_start).total_seconds() / 3600
            if time_range_start and time_range_end
            else None
        )

        return {
            "entity": "GPS",
            "total": total,
            "unique_vehicles": len(plates),
            "records_per_vehicle": round(total / len(plates), 1) if plates else 0,
            "time_range": {
                "start": time_range_start.isoformat() if time_range_start else None,
                "end": time_range_end.isoformat() if time_range_end else None,
                "span_hours": round(time_span_hours, 2) if time_span_hours else None,
            },
            "speed_kmh": {
                "avg": round(sum(speeds) / len(speeds), 1) if speeds else None,
                "max": round(max(speeds), 1) if speeds else None,
                "pct_moving": round(moving / total * 100, 1) if total else 0,
            },
            "accuracy": {
                "avg_m": round(sum(accuracies) / len(accuracies), 1) if accuracies else None,
                "pct_high_accuracy": round(high_accuracy / total * 100, 1) if total else 0,
            },
            "data_quality": {
                "avg_completeness_pct": round(avg_completeness, 1),
                "records_with_speed_pct": round(len(speeds) / total * 100, 1),
                "records_with_accuracy_pct": round(len(accuracies) / total * 100, 1),
            },
        }

    # ── Private helpers ────────────────────────────────────────

    def _to_grid(self, lat: Decimal, lon: Decimal) -> tuple[int, int]:
        """Convert lat/lon to grid cell index relative to Tehran center."""
        grid_lat = int((float(lat) - float(self.TEHRAN_CENTER_LAT)) / float(self.GRID_SIZE))
        grid_lon = int((float(lon) - float(self.TEHRAN_CENTER_LON)) / float(self.GRID_SIZE))
        return (grid_lat, grid_lon)

    @staticmethod
    def _row_completeness(row: dict[str, Any]) -> float:
        """
        Calculate data completeness score for a single row.

        Returns percentage of non-null meaningful fields.
        """
        if not row:
            return 0.0

        # Fields to exclude from completeness calculation
        EXCLUDE_FIELDS = {
            "id", "import_batch_id", "created_at", "updated_at",
            "error_note", "raw_data", "column_mapping",
        }

        total_fields = 0
        filled_fields = 0

        for key, value in row.items():
            if key in EXCLUDE_FIELDS:
                continue
            total_fields += 1
            if value is not None and value != "":
                filled_fields += 1

        if total_fields == 0:
            return 100.0

        return round(filled_fields / total_fields * 100, 1)
