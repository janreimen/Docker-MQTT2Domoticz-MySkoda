from __future__ import annotations

import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleConfig:
    vehicle_id: str
    name: str
    vin: str


def mask_vin(vin: str) -> str:
    if len(vin) <= 6:
        return vin

    return "*" * (len(vin) - 6) + vin[-6:]


def load_vehicles(path: str) -> list[VehicleConfig]:
    with open(
        path,
        encoding="utf-8",
        newline="",
    ) as handle:

        rows = list(csv.DictReader(handle))

    if not rows:
        raise RuntimeError(
            f"No vehicles found in {path}"
        )

    required_columns = {"id", "name", "vin"}

    if not required_columns.issubset(rows[0].keys()):
        raise RuntimeError(
            f"{path} must contain columns: "
            "id,name,vin"
        )

    vehicles: list[VehicleConfig] = []

    for row in rows:
        vehicle_id = row.get("id", "").strip()
        name = row.get("name", "").strip()
        vin = row.get("vin", "").strip()

        if not vehicle_id or not vin:
            continue

        if not name:
            name = vehicle_id

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
