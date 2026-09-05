from __future__ import annotations

import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleConfig:
    vehicle_id: str
    name: str
    vin: str

    @property
    def id(self) -> str:
        """
        Backwards-compatible alias for vehicle_id.
        """
        return self.vehicle_id


def mask_vin(
    vin: str,
) -> str:

    if len(vin) <= 6:
        return vin

    return (
        "*" * (len(vin) - 6)
        + vin[-6:]
    )


def load_vehicles(
    path: str,
) -> list[VehicleConfig]:

    with open(
        path,
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(
            handle
        )

        if reader.fieldnames is None:
            raise RuntimeError(
                f"{path} has no CSV header"
            )

        required_columns = {
            "id",
            "name",
            "vin",
        }

        if not required_columns.issubset(
            set(reader.fieldnames)
        ):
            raise RuntimeError(
                f"{path} must contain columns: "
                "id,name,vin"
            )

        vehicles: list[
            VehicleConfig
        ] = []

        seen_ids: set[str] = set()

        for line_number, row in enumerate(
            reader,
            start=2,
        ):

            vehicle_id = row.get(
                "id",
                "",
            ).strip()

            name = row.get(
                "name",
                "",
            ).strip()

            vin = row.get(
                "vin",
                "",
            ).strip()

            # Ignore completely blank rows.

            if (
                not vehicle_id
                and not name
                and not vin
            ):
                continue

            if not vehicle_id:
                raise RuntimeError(
                    f"{path}:{line_number}: "
                    "vehicle id is required"
                )

            if not vin:
                raise RuntimeError(
                    f"{path}:{line_number}: "
                    f"VIN is required for vehicle "
                    f"'{vehicle_id}'"
                )

            if vehicle_id in seen_ids:
                raise RuntimeError(
                    f"{path}:{line_number}: "
                    f"duplicate vehicle id "
                    f"'{vehicle_id}'"
                )

            if not name:
                name = vehicle_id

            seen_ids.add(
                vehicle_id
            )

            vehicles.append(
                VehicleConfig(
                    vehicle_id=vehicle_id,
                    name=name,
                    vin=vin,
                )
            )

    if not vehicles:
        raise RuntimeError(
            f"No valid vehicles found in {path}"
        )

    return vehicles
