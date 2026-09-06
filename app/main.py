from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import aiohttp
from myskoda import MySkoda

from config import load_config
from domoticz_client import DomoticzClient
from provisioner import provision
from skoda_bridge import SkodaBridge
from vehicles import load_vehicles, mask_vin


VERSION = "0.1.4"


log = logging.getLogger(
    "domoticz_myskoda"
)


def load_device_mapping(
    path: str,
) -> dict[str, Any]:

    file = Path(path)

    if not file.exists():
        return {}

    try:

        data = json.loads(
            file.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError:

        log.warning(
            "Invalid devices.json; "
            "starting with empty mapping"
        )

        return {}

    if not isinstance(
        data,
        dict,
    ):

        log.warning(
            "devices.json does not contain "
            "an object; starting with "
            "empty mapping"
        )

        return {}

    return data


def save_device_mapping(
    path: str,
    mapping: dict[str, Any],
) -> None:
    """
    Atomically replace devices.json.
    """

    file = Path(path)

    file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = (
        json.dumps(
            mapping,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    fd, temporary_path = tempfile.mkstemp(
        prefix=f".{file.name}.",
        suffix=".tmp",
        dir=str(file.parent),
        text=True,
    )

    try:

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:

            handle.write(content)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            file,
        )

        # Best-effort directory fsync.

        try:

            directory_fd = os.open(
                file.parent,
                os.O_DIRECTORY,
            )

            try:
                os.fsync(
                    directory_fd
                )
            finally:
                os.close(
                    directory_fd
                )

        except OSError:
            pass

    except Exception:

        try:
            os.unlink(
                temporary_path
            )
        except OSError:
            pass

        raise


async def update_vehicle(
    domoticz: DomoticzClient,
    device_mapping: dict[str, int],
    snapshot: Any,
    enable_gps: bool,
) -> None:

    # ================================================================
    # Switches
    # ================================================================

    switches = {
        "locked": snapshot.locked,
        "lights_on": snapshot.lights_on,
        "doors_open": snapshot.doors_open,
        "windows_open": snapshot.windows_open,
        "climatisation": snapshot.ac_on,
    }

    for key, value in switches.items():

        if value is None:
            continue

        idx = device_mapping.get(
            key
        )

        if idx is None:
            continue

        await domoticz.set_switch(
            idx,
            value,
        )

    # ================================================================
    # Counters
    # ================================================================

    counters = {
        "range_km": snapshot.range_km,
        "mileage_km": snapshot.mileage_km,
        "inspection_due_days":
            snapshot.inspection_due_days,
    }

    for key, value in counters.items():

        if value is None:
            continue

        idx = device_mapping.get(
            key
        )

        if idx is None:
            continue

        await domoticz.set_custom_counter(
            idx,
            value,
        )

    # ================================================================
    # GPS position
    # ================================================================

    if (
        enable_gps
        and snapshot.position is not None
    ):

        idx = device_mapping.get(
            "position"
        )

        if idx is not None:

            latitude, longitude = (
                snapshot.position
            )

            await domoticz.set_text(
                idx,
                f"{latitude:.6f},"
                f"{longitude:.6f}",
            )


async def run() -> None:

    config = load_config()

    logging.basicConfig(
        level=getattr(
            logging,
            config.log_level,
            logging.INFO,
        ),
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s: "
            "%(message)s"
        ),
    )

    vehicles = load_vehicles(
        config.vehicles_csv_path
    )

    devices = load_device_mapping(
        config.devices_json_path
    )

    log.info(
        "Starting Domoticz-MySkoda v%s",
        VERSION,
    )

    log.info(
        "Loaded %d vehicle(s)",
        len(vehicles),
    )

    timeout = aiohttp.ClientTimeout(
        total=30
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        # ============================================================
        # MySkoda
        # ============================================================

        myskoda = MySkoda(
            session,
            mqtt_enabled=True,
        )

        await myskoda.connect(
            email=config.skoda_username,
            password=config.skoda_password,
        )

        log.info(
            "MySkoda connection ready"
        )

        # ============================================================
        # Domoticz
        # ============================================================

        domoticz = DomoticzClient(
            session=session,
            base_url=config.domoticz_url,
            username=config.domoticz_user,
            password=config.domoticz_password,
        )

        # ============================================================
        # Automatic provisioning
        # ============================================================

        if config.domoticz_provision:

            log.info(
                "Automatic Domoticz provisioning enabled"
            )

            devices = await provision(
                domoticz,
                vehicles,
                devices,
                config.domoticz_hardware_name,
            )

            save_device_mapping(
                config.devices_json_path,
                devices,
            )

            log.info(
                "Domoticz provisioning complete"
            )

        else:

            log.info(
                "Automatic Domoticz provisioning disabled"
            )

        # ============================================================
        # Vehicle bridges
        # ============================================================

        bridges = {
            vehicle.vehicle_id:
                SkodaBridge(
                    myskoda,
                    vehicle.vin,
                    vehicle.name,
                )
            for vehicle in vehicles
        }

        # ============================================================
        # Poll loop
        # ============================================================

        while True:

            for vehicle in vehicles:

                try:

                    log.info(
                        "Polling %s (%s)",
                        vehicle.vehicle_id,
                        mask_vin(
                            vehicle.vin
                        ),
                    )

                    snapshot = await bridges[
                        vehicle.vehicle_id
                    ].snapshot()

                    mapping = devices.get(
                        vehicle.vehicle_id,
                        {},
                    )

                    await update_vehicle(
                        domoticz,
                        mapping,
                        snapshot,
                        config.enable_gps,
                    )

                    log.info(
                        "Poll complete %s: "
                        "locked=%s "
                        "range=%s "
                        "mileage=%s "
                        "inspection=%s",
                        vehicle.vehicle_id,
                        snapshot.locked,
                        snapshot.range_km,
                        snapshot.mileage_km,
                        snapshot.inspection_due_days,
                    )

                except Exception:

                    log.exception(
                        "Polling failed for %s",
                        vehicle.vehicle_id,
                    )

            await asyncio.sleep(
                config.poll_interval_seconds
            )


def main() -> None:
    asyncio.run(
        run()
    )


if __name__ == "__main__":
    main()
