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

        value = cls.dump(value)

        if isinstance(value, dict):

            for key in keys:

                if key in value:
                    return value[key]

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

        if positions is None:

            positions = await self._safe_call(
                "get_positions",
                self.myskoda.get_positions(
                    self.vin
                ),
            )

        if positions is None:
            return None

        positions = self.dump(
            positions
        )

        if isinstance(
            positions,
            dict,
        ):

            for key in (
                "positions",
                "position",
                "items",
                "data",
                "result",
            ):

                if key in positions:
                    positions = positions[key]
                    break

        if isinstance(
            positions,
            list,
        ):

            if not positions:
                return None

            positions = positions[-1]

        positions = self.dump(
            positions
        )

        if not isinstance(
            positions,
            dict,
        ):
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

            nested = self.find(
                positions,
                "position",
                "coordinates",
            )

            nested = self.dump(
                nested
            )

            if isinstance(
                nested,
                dict,
            ):

                latitude = self.find(
                    nested,
                    "latitude",
                    "lat",
                )

                longitude = self.find(
                    nested,
                    "longitude",
                    "lon",
                    "lng",
                )

        if (
            latitude is None
            or longitude is None
        ):
            return None

        try:

            return (
                float(latitude),
                float(longitude),
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

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

        inspection_due_days = self.as_int(
            self.find(
                maintenance_data,
                "inspection_due_in_days",
                "inspection_due_days",
                "inspection_days",
            )
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
