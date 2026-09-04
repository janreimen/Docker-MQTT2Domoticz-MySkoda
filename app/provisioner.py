from __future__ import annotations

import logging
from typing import Any

from domoticz_client import DomoticzClient, DomoticzError


log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Domoticz device definitions
# ----------------------------------------------------------------------

DEVICE_DEFINITIONS: dict[str, dict[str, Any]] = {

    # Virtual switches
    "locked": {
        "suffix": "Locked",
        "sensor_type": 6,
        "switch_type": 19,
        "kind": "switch",
    },

    "lights_on": {
        "suffix": "Lights",
        "sensor_type": 6,
        "switch_type": 0,
        "kind": "switch",
    },

    "doors_open": {
        "suffix": "Doors",
        "sensor_type": 6,
        "switch_type": 11,
        "kind": "switch",
    },

    "windows_open": {
        "suffix": "Windows",
        "sensor_type": 6,
        "switch_type": 11,
        "kind": "switch",
    },

    "climatisation": {
        "suffix": "Climatisation",
        "sensor_type": 6,
        "switch_type": 0,
        "kind": "switch",
    },

    # Absolute Custom Counters
    "range_km": {
        "suffix": "Range",
        "sensor_type": 113,
        "kind": "custom_counter",
        "quantity": "Distance",
        "units": "km",
    },

    "mileage_km": {
        "suffix": "Mileage",
        "sensor_type": 113,
        "kind": "custom_counter",
        "quantity": "Distance",
        "units": "km",
    },

    "inspection_due_days": {
        "suffix": "Inspection",
        "sensor_type": 113,
        "kind": "custom_counter",
        "quantity": "Time",
        "units": "days",
    },

    # Text
    "position": {
        "suffix": "Position",
        "sensor_type": 5,
        "kind": "text",
    },

    # Controls
    "honk_flash": {
        "suffix": "Honk / Flash",
        "sensor_type": 6,
        "switch_type": 9,
        "kind": "switch",
    },

    "window_heating": {
        "suffix": "Window Heating",
        "sensor_type": 6,
        "switch_type": 0,
        "kind": "switch",
    },

    "wakeup": {
        "suffix": "Wakeup",
        "sensor_type": 6,
        "switch_type": 9,
        "kind": "switch",
    },
}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _vehicle_device_name(
    vehicle: Any,
    definition: dict[str, Any],
) -> str:
    """
    Produce the exact Domoticz device name.

    Example:
        Octavia RS [car_001] - Locked
    """
    return (
        f"{vehicle.name} [{vehicle.id}] - "
        f"{definition['suffix']}"
    )


def _find_device_by_name(
    devices: list[dict[str, Any]],
    name: str,
) -> dict[str, Any] | None:

    for device in devices:
        if str(device.get("Name", "")) == name:
            return device

    return None


async def _configure_device(
    client: DomoticzClient,
    idx: int,
    name: str,
    definition: dict[str, Any],
) -> None:

    kind = definition["kind"]

    if kind == "switch":

        await client.configure_switch(
            idx=idx,
            name=name,
            switch_type=int(
                definition["switch_type"]
            ),
        )

    elif kind == "custom_counter":

        await client.configure_custom_counter(
            idx=idx,
            name=name,
            quantity=str(
                definition["quantity"]
            ),
            units=str(
                definition["units"]
            ),
        )

    elif kind == "text":

        await client.configure_text(
            idx=idx,
            name=name,
        )

    else:
        raise RuntimeError(
            f"Unknown Domoticz device kind: {kind}"
        )


# ----------------------------------------------------------------------
# Provisioning
# ----------------------------------------------------------------------

async def provision(
    client: DomoticzClient,
    vehicles: list[Any],
    devices: dict[str, dict[str, int]],
    hardware_name: str,
) -> dict[str, dict[str, int]]:
    """
    Reconcile the required MySkoda Domoticz devices.

    'devices' is the already-loaded devices.json mapping.

    Existing hardware and devices are reused whenever possible.
    Missing hardware/devices are created only when necessary.

    The returned mapping is saved by main.py.
    """

    log.info(
        "Starting Domoticz provisioning for %d vehicle(s)",
        len(vehicles),
    )

    # Keep the supplied mapping as the source of persisted IDXs.
    state = devices if isinstance(devices, dict) else {}

    # --------------------------------------------------------------
    # 1. Discover visible Domoticz devices
    # --------------------------------------------------------------

    try:

        all_devices = await client.get_devices()

        log.info(
            "Domoticz returned %d visible device(s)",
            len(all_devices),
        )

    except DomoticzError as exc:

        log.warning(
            "Could not query Domoticz devices: %s",
            exc,
        )

        # This is important for a restricted Domoticz user.
        #
        # If the user cannot list devices, we can still operate
        # from the persisted devices.json mapping.
        all_devices = []

    # --------------------------------------------------------------
    # 2. Determine hardware IDX
    # --------------------------------------------------------------

    hardware_idx: int | None = None

    # First preference: stored hardware IDX.
    stored_hw = state.get("_hardware_idx")

    if stored_hw is not None:

        try:

            hardware_idx = int(stored_hw)

            log.info(
                "Using stored MySkoda hardware IDX %d",
                hardware_idx,
            )

        except (TypeError, ValueError):

            hardware_idx = None

    # Second preference: derive hardware from an existing device.
    if hardware_idx is None and all_devices:

        for device in all_devices:

            name = str(
                device.get("Name", "")
            )

            if name.startswith("MySkoda"):

                hw = device.get("HardwareID")

                if hw is not None:

                    try:

                        hardware_idx = int(hw)

                        log.info(
                            "Discovered MySkoda hardware IDX %d "
                            "from existing device '%s'",
                            hardware_idx,
                            name,
                        )

                        break

                    except (
                        TypeError,
                        ValueError,
                    ):
                        pass

    # Third preference: query Domoticz hardware directly.
    if hardware_idx is None:

        try:

            hardware = (
                await client.get_hardware_by_name(
                    hardware_name
                )
            )

            if hardware is not None:

                hardware_idx = int(
                    hardware["idx"]
                )

                log.info(
                    "Found existing Domoticz hardware '%s' "
                    "with IDX %d",
                    hardware_name,
                    hardware_idx,
                )

        except DomoticzError as exc:

            log.warning(
                "Could not query Domoticz hardware: %s",
                exc,
            )

    # --------------------------------------------------------------
    # 3. Create hardware only if genuinely missing
    # --------------------------------------------------------------

    if hardware_idx is None:

        log.info(
            "Domoticz hardware '%s' does not exist; "
            "attempting to create it",
            hardware_name,
        )

        hardware_idx = (
            await client.add_dummy_hardware(
                hardware_name
            )
        )

        log.info(
            "Created Domoticz Dummy hardware '%s' "
            "with IDX %d",
            hardware_name,
            hardware_idx,
        )

    else:

        log.info(
            "Reusing existing Domoticz Dummy hardware '%s' "
            "IDX %d",
            hardware_name,
            hardware_idx,
        )

    # --------------------------------------------------------------
    # 4. Devices belonging to our hardware
    # --------------------------------------------------------------

    devices_for_hardware = [
        device
        for device in all_devices
        if str(
            device.get("HardwareID", "")
        ) == str(hardware_idx)
    ]

    log.info(
        "Found %d existing device(s) on MySkoda hardware IDX %d",
        len(devices_for_hardware),
        hardware_idx,
    )

    # --------------------------------------------------------------
    # 5. Reconcile every vehicle
    # --------------------------------------------------------------

    mapping: dict[str, dict[str, int]] = {}

    for vehicle in vehicles:

        vehicle_mapping: dict[str, int] = {}

        stored_vehicle = state.get(
            vehicle.id,
            {},
        )

        if not isinstance(
            stored_vehicle,
            dict,
        ):
            stored_vehicle = {}

        for key, definition in (
            DEVICE_DEFINITIONS.items()
        ):

            name = _vehicle_device_name(
                vehicle,
                definition,
            )

            # ------------------------------------------------------
            # First: exact-name discovery
            # ------------------------------------------------------

            existing = _find_device_by_name(
                devices_for_hardware,
                name,
            )

            if existing is not None:

                idx = int(
                    existing["idx"]
                )

                log.info(
                    "Reusing existing device IDX %d: %s",
                    idx,
                    name,
                )

                # Existing devices may have been created previously
                # with incorrect sensor types. Reconfigure them.
                try:

                    await _configure_device(
                        client=client,
                        idx=idx,
                        name=name,
                        definition=definition,
                    )

                except DomoticzError as exc:

                    # Restricted users may be able to update values
                    # but not change device configuration.
                    #
                    # That is not fatal because the device itself
                    # already exists and can still be mapped.
                    log.warning(
                        "Could not configure existing device "
                        "IDX %d '%s': %s",
                        idx,
                        name,
                        exc,
                    )

                vehicle_mapping[key] = idx
                continue

            # ------------------------------------------------------
            # Second: persisted state mapping
            # ------------------------------------------------------

            stored_idx = stored_vehicle.get(
                key
            )

            if stored_idx is not None:

                try:

                    idx = int(
                        stored_idx
                    )

                    log.info(
                        "Reusing state-mapped device IDX %d: %s",
                        idx,
                        name,
                    )

                    vehicle_mapping[key] = idx
                    continue

                except (
                    TypeError,
                    ValueError,
                ):
                    pass

            # ------------------------------------------------------
            # Third: genuinely missing device
            # ------------------------------------------------------

            log.warning(
                "Domoticz device '%s' does not exist; "
                "attempting to create it",
                name,
            )

            idx = (
                await client.create_virtual_sensor(
                    hardware_idx=hardware_idx,
                    sensor_name=name,
                    sensor_type=int(
                        definition["sensor_type"]
                    ),
                )
            )

            await _configure_device(
                client=client,
                idx=idx,
                name=name,
                definition=definition,
            )

            log.info(
                "Created device IDX %d: %s",
                idx,
                name,
            )

            vehicle_mapping[key] = idx

            # Add to local discovery list.
            devices_for_hardware.append(
                {
                    "idx": idx,
                    "Name": name,
                    "HardwareID": hardware_idx,
                }
            )

        mapping[vehicle.id] = vehicle_mapping

    # --------------------------------------------------------------
    # 6. Persisted mapping
    # --------------------------------------------------------------

    result: dict[str, dict[str, int]] = {
        "_hardware_idx": hardware_idx,  # type: ignore[dict-item]
    }

    result.update(mapping)

    log.info(
        "Domoticz provisioning mapping prepared "
        "for %d vehicle(s)",
        len(vehicles),
    )

    return result
