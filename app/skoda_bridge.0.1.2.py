from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any


log = logging.getLogger(__name__)


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


def dump(value: Any) -> Any:

    if value is None:
        return None

    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass

    if isinstance(value, dict):
        return {
            key: dump(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            dump(item)
            for item in value
        ]

    if hasattr(value, "__dict__"):
        try:
            return {
                key: dump(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        except Exception:
            pass

    return value


def find(
    value: Any,
    names: set[str],
) -> Any:

    value = dump(value)

    if isinstance(value, dict):

        for key, item in value.items():

            normalized = (
                str(key)
                .lower()
                .replace("-", "_")
            )

            if normalized in names:
                return item

        for item in value.values():

            result = find(item, names)

            if result is not None:
                return result

    elif isinstance(value, list):

        for item in value:

            result = find(item, names)

            if result is not None:
                return result

    return None


def as_bool(value: Any) -> bool | None:

    if isinstance(value, bool):
        return value

    if value is None:
        return None

    text = str(value).strip().lower()

    if text in {
        "true",
        "1",
        "on",
        "yes",
        "open",
        "unlocked",
    }:
        return True

    if text in {
        "false",
        "0",
        "off",
        "no",
        "closed",
        "locked",
    }:
        return False

    return None


def as_int(value: Any) -> int | None:

    if value is None:
        return None

    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return None


class SkodaBridge:

    def __init__(
        self,
        myskoda: Any,
        vin: str,
        enable_gps: bool = True,
    ) -> None:

        self.myskoda = myskoda
        self.vin = vin
        self.enable_gps = enable_gps

    async def _position(
        self,
    ) -> tuple[float, float] | None:

        if not self.enable_gps:
            return None

        positions = await self.myskoda.get_positions(
            self.vin
        )

        data = dump(positions)

        if not isinstance(data, dict):
            return None

        position_list = data.get("positions", [])

        if not isinstance(position_list, list):
            return None

        for position in position_list:

            if not isinstance(position, dict):
                continue

            gps = position.get(
                "gps_coordinates",
                {},
            )

            if not isinstance(gps, dict):
                continue

            latitude = gps.get("latitude")
            longitude = gps.get("longitude")

            if latitude is None or longitude is None:
                continue

            try:
                return (
                    float(latitude),
                    float(longitude),
                )
            except (TypeError, ValueError):
                continue

        return None

    async def snapshot(self) -> VehicleSnapshot:

        (
            status,
            driving_range,
            health,
            maintenance,
            air_conditioning,
        ) = await asyncio.gather(
            self.myskoda.get_status(self.vin),
            self.myskoda.get_driving_range(self.vin),
            self.myskoda.get_health(self.vin),
            self.myskoda.get_maintenance(self.vin),
            self.myskoda.get_air_conditioning(self.vin),
        )

        position = await self._position()

        return VehicleSnapshot(
            locked=as_bool(
                find(
                    status,
                    {
                        "doors_locked",
                        "locked",
                    },
                )
            ),

            lights_on=as_bool(
                find(
                    status,
                    {
                        "lights_on",
                        "lights",
                    },
                )
            ),

            doors_open=as_bool(
                find(
                    status,
                    {
                        "doors_open",
                        "door_open",
                    },
                )
            ),

            windows_open=as_bool(
                find(
                    status,
                    {
                        "windows_open",
                        "window_open",
                    },
                )
            ),

            ac_on=as_bool(
                find(
                    air_conditioning,
                    {
                        "state",
                        "ac_on",
                        "air_conditioning_on",
                    },
                )
            ),

            range_km=as_int(
                find(
                    driving_range,
                    {
                        "total_range_in_km",
                        "range_in_km",
                        "total_range",
                    },
                )
            ),

            mileage_km=as_int(
                find(
                    health,
                    {
                        "mileage_in_km",
                        "mileage",
                        "odometer",
                    },
                )
            ),

            inspection_due_days=as_int(
                find(
                    maintenance,
                    {
                        "inspection_due_in_days",
                        "inspection_due_days",
                    },
                )
            ),

            position=position,
        )
