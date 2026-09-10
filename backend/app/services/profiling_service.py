"""
Profiling Service.

Analyzes imported data to provide quality metrics, distribution statistics,
and actionable insights for logistics optimization.

This service runs AFTER validation/import and is intentionally separate from
ValidationService. It does not decide whether a row is valid; it only
profiles data that has already been parsed/validated/imported.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.schemas.import_schema import EntityTypeEnum


class ProfilingService:
    """
    Analyzes data quality and distribution patterns across imported entities.

    Usage:
        service = ProfilingService()
        report = service.profile(EntityTypeEnum.STORE, stores_data)
    """

    TEHRAN_CENTER_LAT: Decimal = Decimal("35.6892")
    TEHRAN_CENTER_LON: Decimal = Decimal("51.3890")

    GRID_SIZE: Decimal = Decimal("0.01")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def profile(
        self,
        entity_type: EntityTypeEnum,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a profiling report for an entity type.

        Input rows are expected to use normalized/model field names.
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
            raise ValueError(
                f"No profiler for entity type: {entity_type}"
            )

        return profiler(rows)

    # ------------------------------------------------------------------
    # Store profiling
    # ------------------------------------------------------------------

    def profile_stores(
        self,
        stores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total = len(stores)

        if total == 0:
            return {
                "entity": EntityTypeEnum.STORE.value,
                "total": 0,
                "message": "No store data to profile.",
            }

        coords_present = 0
        coords_missing = 0

        categories: Counter[str] = Counter()
        statuses: Counter[str] = Counter()
        grid_counts: Counter[tuple[int, int]] = Counter()

        service_times: list[int] = []
        completeness_scores: list[float] = []

        for store in stores:
            lat = self._to_decimal(store.get("latitude"))
            lon = self._to_decimal(store.get("longitude"))

            if lat is not None and lon is not None:
                coords_present += 1

                try:
                    grid_key = self._to_grid(lat, lon)
                    grid_counts[grid_key] += 1
                except (ValueError, TypeError):
                    pass
            else:
                coords_missing += 1

            category = store.get("category")
            if self._has_value(category):
                categories[str(category).strip()] += 1

            status = store.get("status")
            statuses[str(status).strip() if self._has_value(status) else "unknown"] += 1

            service_time = store.get("service_time_min")

            if service_time is not None:
                try:
                    service_times.append(int(service_time))
                except (ValueError, TypeError):
                    pass

            completeness_scores.append(
                self._row_completeness(store)
            )

        avg_service_time = (
            sum(service_times) / len(service_times)
            if service_times
            else None
        )

        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        top_locations = []

        for grid, count in grid_counts.most_common(10):
            top_locations.append(
                {
                    "grid": f"{grid[0]},{grid[1]}",
                    "approx_lat": (
                        float(grid[0]) * float(self.GRID_SIZE)
                        + float(self.TEHRAN_CENTER_LAT)
                    ),
                    "approx_lon": (
                        float(grid[1]) * float(self.GRID_SIZE)
                        + float(self.TEHRAN_CENTER_LON)
                    ),
                    "count": count,
                }
            )

        return {
            "entity": EntityTypeEnum.STORE.value,
            "total": total,
            "coordinates": {
                "present": coords_present,
                "missing": coords_missing,
                "coverage_pct": round(
                    coords_present / total * 100,
                    1,
                ),
            },
            "categories": dict(categories.most_common()),
            "status_distribution": dict(statuses),
            "service_time": {
                "avg_minutes": (
                    round(avg_service_time, 1)
                    if avg_service_time is not None
                    else None
                ),
                "min": min(service_times) if service_times else None,
                "max": max(service_times) if service_times else None,
            },
            "density": {
                "unique_grids": len(grid_counts),
                "max_grid_count": (
                    max(grid_counts.values())
                    if grid_counts
                    else 0
                ),
                "top_clusters": top_locations,
            },
            "data_quality": {
                "avg_completeness_pct": round(
                    avg_completeness,
                    1,
                ),
                "rows_with_coords_pct": round(
                    coords_present / total * 100,
                    1,
                ),
            },
        }

    # ------------------------------------------------------------------
    # Order profiling
    # ------------------------------------------------------------------

    def profile_orders(
        self,
        orders: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total = len(orders)

        if total == 0:
            return {
                "entity": EntityTypeEnum.ORDER.value,
                "total": 0,
                "message": "No order data to profile.",
            }

        weights: list[float] = []
        volumes: list[float] = []
        item_counts: list[int] = []

        store_codes: set[str] = set()
        statuses: Counter[str] = Counter()

        coord_count = 0
        completeness_scores: list[float] = []

        for order in orders:
            weight = order.get("weight_kg")
            if weight is not None:
                try:
                    weights.append(float(weight))
                except (ValueError, TypeError):
                    pass

            volume = order.get("volume_m3")
            if volume is not None:
                try:
                    volumes.append(float(volume))
                except (ValueError, TypeError):
                    pass

            item_count = order.get("item_count")
            if item_count is not None:
                try:
                    item_counts.append(int(item_count))
                except (ValueError, TypeError):
                    pass

            store_code = order.get("store_code")
            if self._has_value(store_code):
                store_codes.add(str(store_code).strip())

            status = order.get("status")
            statuses[
                str(status).strip()
                if self._has_value(status)
                else "unknown"
            ] += 1

            lat = self._to_decimal(order.get("latitude"))
            lon = self._to_decimal(order.get("longitude"))

            if lat is not None and lon is not None:
                coord_count += 1

            completeness_scores.append(
                self._row_completeness(order)
            )

        avg_completeness = (
            sum(completeness_scores)
            / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        return {
            "entity": EntityTypeEnum.ORDER.value,
            "total": total,
            "unique_stores": len(store_codes),
            "orders_per_store": (
                round(total / len(store_codes), 1)
                if store_codes
                else 0
            ),
            "weight_kg": {
                "avg": (
                    round(sum(weights) / len(weights), 2)
                    if weights
                    else None
                ),
                "min": round(min(weights), 2) if weights else None,
                "max": round(max(weights), 2) if weights else None,
                "total": round(sum(weights), 2) if weights else 0,
            },
            "volume_m3": {
                "avg": (
                    round(sum(volumes) / len(volumes), 3)
                    if volumes
                    else None
                ),
                "total": round(sum(volumes), 3) if volumes else 0,
            },
            "items": {
                "avg": (
                    round(sum(item_counts) / len(item_counts), 1)
                    if item_counts
                    else None
                ),
                "total": sum(item_counts) if item_counts else 0,
            },
            "coordinates_coverage_pct": round(
                coord_count / total * 100,
                1,
            ),
            "status_distribution": dict(statuses),
            "data_quality": {
                "avg_completeness_pct": round(
                    avg_completeness,
                    1,
                ),
            },
        }

    # ------------------------------------------------------------------
    # Vehicle profiling
    # ------------------------------------------------------------------

    def profile_vehicles(
        self,
        vehicles: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total = len(vehicles)

        if total == 0:
            return {
                "entity": EntityTypeEnum.FLEET.value,
                "total": 0,
                "message": "No vehicle data to profile.",
            }

        types: Counter[str] = Counter()
        capacities: list[float] = []
        volumes: list[float] = []
        cost_per_km: list[float] = []
        fixed_costs: list[float] = []

        statuses: Counter[str] = Counter()

        coord_count = 0
        completeness_scores: list[float] = []

        for vehicle in vehicles:
            vehicle_type = vehicle.get("vehicle_type")

            if self._has_value(vehicle_type):
                types[str(vehicle_type).strip()] += 1

            capacity = vehicle.get("capacity_kg")
            if capacity is not None:
                try:
                    capacities.append(float(capacity))
                except (ValueError, TypeError):
                    pass

            volume = vehicle.get("volume_m3")
            if volume is not None:
                try:
                    volumes.append(float(volume))
                except (ValueError, TypeError):
                    pass

            cost = vehicle.get("cost_per_km")
            if cost is not None:
                try:
                    cost_per_km.append(float(cost))
                except (ValueError, TypeError):
                    pass

            fixed_cost = vehicle.get("fixed_cost")
            if fixed_cost is not None:
                try:
                    fixed_costs.append(float(fixed_cost))
                except (ValueError, TypeError):
                    pass

            status = vehicle.get("status")
            statuses[
                str(status).strip()
                if self._has_value(status)
                else "unknown"
            ] += 1

            lat = self._to_decimal(vehicle.get("latitude"))
            lon = self._to_decimal(vehicle.get("longitude"))

            if lat is not None and lon is not None:
                coord_count += 1

            completeness_scores.append(
                self._row_completeness(vehicle)
            )

        avg_completeness = (
            sum(completeness_scores)
            / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        return {
            "entity": EntityTypeEnum.FLEET.value,
            "total": total,
            "type_distribution": dict(types),
            "capacity_kg": {
                "avg": (
                    round(sum(capacities) / len(capacities), 1)
                    if capacities
                    else None
                ),
                "min": round(min(capacities), 1) if capacities else None,
                "max": round(max(capacities), 1) if capacities else None,
                "total": round(sum(capacities), 1) if capacities else 0,
            },
            "volume_m3": {
                "total": round(sum(volumes), 1) if volumes else 0,
            },
            "costs": {
                "avg_cost_per_km": (
                    round(sum(cost_per_km) / len(cost_per_km), 2)
                    if cost_per_km
                    else None
                ),
                "avg_fixed_cost": (
                    round(sum(fixed_costs) / len(fixed_costs), 2)
                    if fixed_costs
                    else None
                ),
            },
            "coordinates_coverage_pct": round(
                coord_count / total * 100,
                1,
            ),
            "status_distribution": dict(statuses),
            "data_quality": {
                "avg_completeness_pct": round(
                    avg_completeness,
                    1,
                ),
            },
        }

    # ------------------------------------------------------------------
    # Driver profiling
    # ------------------------------------------------------------------

    def profile_drivers(
        self,
        drivers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total = len(drivers)

        if total == 0:
            return {
                "entity": EntityTypeEnum.DRIVER.value,
                "total": 0,
                "message": "No driver data to profile.",
            }

        statuses: Counter[str] = Counter()

        expired_licenses = 0
        valid_licenses = 0
        coord_count = 0

        completeness_scores: list[float] = []

        now = datetime.now(timezone.utc)

        for driver in drivers:
            status = driver.get("status")

            statuses[
                str(status).strip()
                if self._has_value(status)
                else "unknown"
            ] += 1

            expiry = driver.get("license_expiry")

            if expiry:
                try:
                    expiry_date = self._normalize_datetime(expiry)

                    if expiry_date is not None:
                        if expiry_date < now:
                            expired_licenses += 1
                        else:
                            valid_licenses += 1

                except (ValueError, TypeError):
                    pass

            lat = self._to_decimal(driver.get("latitude"))
            lon = self._to_decimal(driver.get("longitude"))

            if lat is not None and lon is not None:
                coord_count += 1

            completeness_scores.append(
                self._row_completeness(driver)
            )

        avg_completeness = (
            sum(completeness_scores)
            / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        return {
            "entity": EntityTypeEnum.DRIVER.value,
            "total": total,
            "status_distribution": dict(statuses),
            "licenses": {
                "valid": valid_licenses,
                "expired": expired_licenses,
                "unknown": (
                    total
                    - valid_licenses
                    - expired_licenses
                ),
                "expired_pct": round(
                    expired_licenses / total * 100,
                    1,
                ),
            },
            "coordinates_coverage_pct": round(
                coord_count / total * 100,
                1,
            ),
            "data_quality": {
                "avg_completeness_pct": round(
                    avg_completeness,
                    1,
                ),
            },
        }

    # ------------------------------------------------------------------
    # GPS profiling
    # ------------------------------------------------------------------

    def profile_gps_records(
        self,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total = len(records)

        if total == 0:
            return {
                "entity": EntityTypeEnum.GPS.value,
                "total": 0,
                "message": "No GPS data to profile.",
            }

        plates: set[str] = set()
        speeds: list[float] = []
        accuracies: list[float] = []
        headings: list[float] = []
        timestamps: list[datetime] = []

        completeness_scores: list[float] = []

        high_accuracy = 0
        moving = 0

        for record in records:
            plate = record.get("vehicle_plate")

            if self._has_value(plate):
                plates.add(str(plate).strip())

            speed = record.get("speed_kmh")

            if speed is not None:
                try:
                    speed_value = float(speed)
                    speeds.append(speed_value)

                    if speed_value > 5:
                        moving += 1

                except (ValueError, TypeError):
                    pass

            accuracy = record.get("accuracy_m")

            if accuracy is not None:
                try:
                    accuracy_value = float(accuracy)
                    accuracies.append(accuracy_value)

                    if accuracy_value < 10:
                        high_accuracy += 1

                except (ValueError, TypeError):
                    pass

            heading = record.get("heading")

            if heading is not None:
                try:
                    headings.append(float(heading))
                except (ValueError, TypeError):
                    pass

            timestamp = record.get("timestamp")

            if timestamp:
                try:
                    normalized_timestamp = self._normalize_datetime(
                        timestamp
                    )

                    if normalized_timestamp is not None:
                        timestamps.append(normalized_timestamp)

                except (ValueError, TypeError):
                    pass

            completeness_scores.append(
                self._row_completeness(record)
            )

        avg_completeness = (
            sum(completeness_scores)
            / len(completeness_scores)
            if completeness_scores
            else 0.0
        )

        time_range_start = min(timestamps) if timestamps else None
        time_range_end = max(timestamps) if timestamps else None

        time_span_hours = None

        if time_range_start and time_range_end:
            time_span_hours = (
                time_range_end - time_range_start
            ).total_seconds() / 3600

        return {
            "entity": EntityTypeEnum.GPS.value,
            "total": total,
            "unique_vehicles": len(plates),
            "records_per_vehicle": (
                round(total / len(plates), 1)
                if plates
                else 0
            ),
            "time_range": {
                "start": (
                    time_range_start.isoformat()
                    if time_range_start
                    else None
                ),
                "end": (
                    time_range_end.isoformat()
                    if time_range_end
                    else None
                ),
                "span_hours": (
                    round(time_span_hours, 2)
                    if time_span_hours is not None
                    else None
                ),
            },
            "speed_kmh": {
                "avg": (
                    round(sum(speeds) / len(speeds), 1)
                    if speeds
                    else None
                ),
                "max": round(max(speeds), 1) if speeds else None,
                "pct_moving": round(
                    moving / total * 100,
                    1,
                ),
            },
            "accuracy": {
                "avg_m": (
                    round(sum(accuracies) / len(accuracies), 1)
                    if accuracies
                    else None
                ),
                "pct_high_accuracy": round(
                    high_accuracy / total * 100,
                    1,
                ),
            },
            "data_quality": {
                "avg_completeness_pct": round(
                    avg_completeness,
                    1,
                ),
                "records_with_speed_pct": round(
                    len(speeds) / total * 100,
                    1,
                ),
                "records_with_accuracy_pct": round(
                    len(accuracies) / total * 100,
                    1,
                ),
            },
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _to_grid(
        self,
        lat: Decimal,
        lon: Decimal,
    ) -> tuple[int, int]:
        """Convert lat/lon to a grid cell relative to Tehran center."""

        grid_lat = int(
            (
                float(lat)
                - float(self.TEHRAN_CENTER_LAT)
            )
            / float(self.GRID_SIZE)
        )

        grid_lon = int(
            (
                float(lon)
                - float(self.TEHRAN_CENTER_LON)
            )
            / float(self.GRID_SIZE)
        )

        return grid_lat, grid_lon

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        """Safely convert a value to Decimal."""

        if value is None:
            return None

        if isinstance(value, Decimal):
            return value

        try:
            if hasattr(value, "item"):
                value = value.item()
        except Exception:
            pass

        value_str = str(value).strip()

        if not value_str:
            return None

        try:
            return Decimal(value_str)
        except Exception:
            return None

    @staticmethod
    def _has_value(value: Any) -> bool:
        """Return True when a value is meaningfully populated."""

        if value is None:
            return False

        if isinstance(value, str):
            return bool(value.strip())

        try:
            if hasattr(value, "item"):
                value = value.item()
        except Exception:
            pass

        try:
            if isinstance(value, float) and value != value:
                return False
        except Exception:
            pass

        return True

    @staticmethod
    def _normalize_datetime(value: Any) -> datetime | None:
        """
        Normalize datetime values to timezone-aware UTC.

        This prevents comparisons between naive and aware datetimes.
        """

        if value is None:
            return None

        if isinstance(value, str):
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        elif isinstance(value, datetime):
            parsed = value
        else:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _row_completeness(
        row: dict[str, Any],
    ) -> float:
        """
        Calculate data completeness percentage for one row.

        Import/database metadata and technical fields are excluded.
        """

        if not row:
            return 0.0

        exclude_fields = {
            "id",
            "import_batch_id",
            "created_at",
            "updated_at",
            "error_note",
            "raw_data",
            "column_mapping",
        }

        total_fields = 0
        filled_fields = 0

        for key, value in row.items():
            if key in exclude_fields:
                continue

            total_fields += 1

            if ProfilingService._has_value(value):
                filled_fields += 1

        if total_fields == 0:
            return 100.0

        return round(
            filled_fields / total_fields * 100,
            1,
        )