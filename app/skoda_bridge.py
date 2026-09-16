from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any


log = logging.getLogger("myskoda")


@dataclass
class VehicleSnapshot:
    locked: bool | None = None
    lights_on: bool | None = None
    doors_open: bool | None = None
    windows_open: bool | None = None
    ac_on: bool | None = None

    range_km: int | None = None
    mileage_km: int | None = None
    inspection_due_days: int | None = None

    position: tuple[float, float] | None = None


class SkodaBridge:

    def __init__(
        self,
        myskoda: Any,
        vin: str,
        vehicle_name: str,
    ) -> None:
        self.myskoda = myskoda
        self.vin = vin
        self.vehicle_name = vehicle_name

    # ================================================================
    # Generic helpers
    # ================================================================

    @staticmethod
    def dump(
        value: Any,
    ) -> Any:

        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if hasattr(
            value,
            "model_dump",
        ):
            try:
                return value.model_dump()
            except Exception:
                pass

        if hasattr(
            value,
            "dict",
        ):
            try:
                return value.dict()
            except Exception:
                pass

        if hasattr(
            value,
            "__dict__",
        ):
            try:
                return vars(value)
            except Exception:
                pass

        return value

    @classmethod
    def find(
        cls,
        value: Any,
        *keys: str,
    ) -> Any:
        """
        Recursively find the first matching field.

        MySkoda responses can contain nested dictionaries, lists, and
        Pydantic-style model objects. The API also uses camelCase in
        some raw responses while the Python models normally expose
        snake_case fields, so both forms are accepted.
        """

        if value is None:
            return None

        value = cls.dump(value)

        wanted: set[str] = set(keys)

        # Add camelCase equivalents.
        for key in tuple(wanted):
            if "_" in key:
                parts = key.split("_")

                wanted.add(
                    parts[0]
                    + "".join(
                        part.capitalize()
                        for part in parts[1:]
                    )
                )

        # Dictionary.
        if isinstance(
            value,
            dict,
        ):

            # Prefer fields at the current level.
            for key in wanted:
                if key in value:
                    return value[key]

            # Then recursively inspect nested values.
            for nested in value.values():

                result = cls.find(
                    nested,
                    *wanted,
                )

                if result is not None:
                    return result

            return None

        # Lists / tuples.
        if isinstance(
            value,
            (list, tuple),
        ):

            for item in value:

                result = cls.find(
                    item,
                    *wanted,
                )

                if result is not None:
                    return result

        return None

    @staticmethod
    def as_bool(
        value: Any,
    ) -> bool | None:

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            (int, float),
        ):
            return bool(value)

        if isinstance(
            value,
            str,
        ):

            normalized = (
                value.strip().lower()
            )

            if normalized in {
                "true",
                "1",
                "yes",
                "on",
                "locked",
                "active",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "off",
                "unlocked",
                "inactive",
            }:
                return False

        return None

    @staticmethod
    def as_int(
        value: Any,
    ) -> int | None:

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return int(value)

        if isinstance(
            value,
            int,
        ):
            return value

        if isinstance(
            value,
            float,
        ):
            return int(value)

        if isinstance(
            value,
            str,
        ):

            try:

                value = value.strip()

                if not value:
                    return None

                return int(
                    float(value)
                )

            except ValueError:
                return None

        return None

    # ================================================================
    # Safe API access
    # ================================================================

    async def _safe_call(
        self,
        name: str,
        coroutine: Any,
    ) -> Any:

        try:

            return await coroutine

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            log.warning(
                "%s failed for %s: %s",
                name,
                self.vehicle_name,
                exc,
            )

            return None

    # ================================================================
    # Position
    # ================================================================

    async def _position(
        self,
        positions: Any = None,
    ) -> tuple[float, float] | None:
        """
        Extract the latest vehicle GPS position.

        Handles nested structures such as:

            positions[]
              -> gpsCoordinates
                   -> latitude
                   -> longitude

        as well as simpler position/coordinate structures.
        """

        if positions is None:

            positions = await self._safe_call(
                "get_positions",
                self.myskoda.get_positions(
                    self.vin
                ),
            )

        if positions is None:
            return None

        latitude = self.find(
            positions,
            "latitude",
            "lat",
        )

        longitude = self.find(
            positions,
            "longitude",
            "lon",
            "lng",
        )

        if (
            latitude is None
            or longitude is None
        ):

            log.debug(
                "No GPS coordinates found for %s",
                self.vehicle_name,
            )

            return None

        try:

            result = (
                float(latitude),
                float(longitude),
            )

        except (
            TypeError,
            ValueError,
        ):

            log.warning(
                "Invalid GPS coordinates for %s: "
                "latitude=%r longitude=%r",
                self.vehicle_name,
                latitude,
                longitude,
            )

            return None

        log.debug(
            "GPS position for %s: %.6f,%.6f",
            self.vehicle_name,
            result[0],
            result[1],
        )

        return result

    # ================================================================
    # Snapshot
    # ================================================================

    async def snapshot(
        self,
    ) -> VehicleSnapshot:

        (
            status,
            driving_range,
            health,
            maintenance,
            air_conditioning,
            positions,
        ) = await asyncio.gather(

            self._safe_call(
                "get_status",
                self.myskoda.get_status(
                    self.vin
                ),
            ),

            self._safe_call(
                "get_driving_range",
                self.myskoda.get_driving_range(
                    self.vin
                ),
            ),

            self._safe_call(
                "get_health",
                self.myskoda.get_health(
                    self.vin
                ),
            ),

            self._safe_call(
                "get_maintenance",
                self.myskoda.get_maintenance(
                    self.vin
                ),
            ),

            self._safe_call(
                "get_air_conditioning",
                self.myskoda.get_air_conditioning(
                    self.vin
                ),
            ),

            self._safe_call(
                "get_positions",
                self.myskoda.get_positions(
                    self.vin
                ),
            ),

            return_exceptions=False,
        )

        status_data = self.dump(
            status
        )

        range_data = self.dump(
            driving_range
        )

        health_data = self.dump(
            health
        )

        maintenance_data = self.dump(
            maintenance
        )

        ac_data = self.dump(
            air_conditioning
        )

        # ============================================================
        # Status
        # ============================================================

        locked = self.as_bool(
            self.find(
                status_data,
                "doors_locked",
                "locked",
            )
        )

        lights_on = self.as_bool(
            self.find(
                status_data,
                "lights_on",
                "lights",
            )
        )

        doors_open = self.as_bool(
            self.find(
                status_data,
                "doors_open",
                "door_open",
            )
        )

        windows_open = self.as_bool(
            self.find(
                status_data,
                "windows_open",
                "window_open",
            )
        )

        # ============================================================
        # Air conditioning
        # ============================================================

        ac_on = self.as_bool(
            self.find(
                ac_data,
                "state",
                "ac_on",
                "air_conditioning_on",
            )
        )

        if ac_on is None:

            state = self.find(
                ac_data,
                "state",
            )

            if isinstance(
                state,
                str,
            ):

                normalized = (
                    state.strip().lower()
                )

                if normalized in {
                    "on",
                    "active",
                    "running",
                    "heating",
                    "cooling",
                }:
                    ac_on = True

                elif normalized in {
                    "off",
                    "inactive",
                    "stopped",
                    "idle",
                }:
                    ac_on = False

        # ============================================================
        # Range
        # ============================================================

        range_km = self.as_int(
            self.find(
                range_data,
                "total_range_in_km",
                "range_in_km",
                "total_range",
                "range",
            )
        )

        # ============================================================
        # Mileage
        # ============================================================

        mileage_km = self.as_int(
            self.find(
                health_data,
                "mileage_in_km",
                "mileage",
                "odometer",
            )
        )

        if mileage_km is None:

            mileage_km = self.as_int(
                self.find(
                    status_data,
                    "mileage_in_km",
                    "mileage",
                    "odometer",
                )
            )

        # ============================================================
        # Inspection
        # ============================================================

        inspection_raw = self.find(
            maintenance_data,
            "inspection_due_in_days",
            "inspection_due_days",
            "inspection_days",
        )

        inspection_due_days = self.as_int(
            inspection_raw
        )

        if inspection_due_days is None:

            log.debug(
                "No inspection due value found for %s",
                self.vehicle_name,
            )

        else:

            log.debug(
                "Inspection due for %s: %d days",
                self.vehicle_name,
                inspection_due_days,
            )

        # ============================================================
        # Position
        # ============================================================

        position = await self._position(
            positions
        )

        snapshot = VehicleSnapshot(
            locked=locked,
            lights_on=lights_on,
            doors_open=doors_open,
            windows_open=windows_open,
            ac_on=ac_on,
            range_km=range_km,
            mileage_km=mileage_km,
            inspection_due_days=inspection_due_days,
            position=position,
        )

        log.debug(
            "Snapshot for %s: %s",
            self.vehicle_name,
            snapshot,
        )

        return snapshot
