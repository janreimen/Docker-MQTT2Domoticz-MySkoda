from __future__ import annotations

import logging
from typing import Any

from domoticz_client import DomoticzClient, DomoticzError


log = logging.getLogger(__name__)


DEVICE_DEFINITIONS: dict[str, dict[str, Any]] = {
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
    "position": {
        "suffix": "Position",
        "sensor_type": 5,
        "kind": "text",
    },
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


def _vehicle_id(vehicle: Any) -> str:
    value = getattr(
        vehicle,
        "vehicle_id",
        None,
    )

    if value:
        return str(value)

    value = getattr(
        vehicle,
        "id",
        None,
    )

    if value:
        return str(value)

    raise RuntimeError(
        "Vehicle object has neither "
        "vehicle_id nor id"
    )


def _vehicle_device_name(
    vehicle: Any,
    definition: dict[str, Any],
) -> str:
    return (
        f"{vehicle.name} "
        f"[{_vehicle_id(vehicle)}] - "
        f"{definition['suffix']}"
    )


def _safe_int(
    value: Any,
) -> int | None:
    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _find_device_by_name(
    devices: list[dict[str, Any]],
    name: str,
) -> dict[str, Any] | None:

    for device in devices:
        if str(
            device.get("Name", "")
        ) == name:
            return device

    return None


def _find_device_by_idx(
    devices: list[dict[str, Any]],
    idx: int,
) -> dict[str, Any] | None:

    for device in devices:
        device_idx = _safe_int(
            device.get("idx")
        )

        if device_idx == idx:
            return device

    return None


def _device_belongs_to_hardware(
    device: dict[str, Any],
    hardware_idx: int,
) -> bool:

    device_hw = _safe_int(
        device.get("HardwareID")
    )

    return device_hw == hardware_idx


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
            f"Unknown Domoticz device kind: "
            f"{kind}"
        )


async def _discover_hardware_idx(
    client: DomoticzClient,
    state: dict[str, Any],
    all_devices: list[dict[str, Any]],
    hardware_name: str,
) -> int | None:
    """
    Determine the existing MySkoda hardware IDX.

    Priority:

    1. Validate persisted hardware IDX.
    2. Search hardware by exact name.
    3. Derive hardware from an existing MySkoda device.
    4. Return None so the caller can create it.
    """

    stored_hw = _safe_int(
        state.get("_hardware_idx")
    )

    if stored_hw is not None:

        try:
            hardware = await client.get_hardware()

            for item in hardware:

                item_idx = _safe_int(
                    item.get("idx")
                )

                if item_idx != stored_hw:
                    continue

                item_name = str(
                    item.get("Name", "")
                )

                if item_name == hardware_name:

                    log.info(
                        "Validated stored MySkoda "
                        "hardware IDX %d",
                        stored_hw,
                    )

                    return stored_hw

                log.warning(
                    "Stored MySkoda hardware IDX %d "
                    "exists but has name '%s'; "
                    "searching by exact hardware name",
                    stored_hw,
                    item_name,
                )

        except DomoticzError as exc:

            log.warning(
                "Could not validate stored hardware "
                "IDX %d: %s",
                stored_hw,
                exc,
            )

            return stored_hw

    # Exact hardware name has priority.

    try:

        hardware = await client.get_hardware_by_name(
            hardware_name
        )

        if hardware is not None:

            hardware_idx = _safe_int(
                hardware.get("idx")
            )

            if hardware_idx is not None:

                log.info(
                    "Found existing Domoticz hardware "
                    "'%s' with IDX %d",
                    hardware_name,
                    hardware_idx,
                )

                return hardware_idx

    except DomoticzError as exc:

        log.warning(
            "Could not query Domoticz hardware: %s",
            exc,
        )

    # Fall back to an existing MySkoda device.

    for device in all_devices:

        name = str(
            device.get("Name", "")
        )

        if not name.startswith(
            "MySkoda"
        ):
            continue

        hardware_idx = _safe_int(
            device.get("HardwareID")
        )

        if hardware_idx is not None:

            log.info(
                "Discovered MySkoda hardware "
                "IDX %d from existing device '%s'",
                hardware_idx,
                name,
            )

            return hardware_idx

    return None


async def provision(
    client: DomoticzClient,
    vehicles: list[Any],
    devices: dict[str, dict[str, int]],
    hardware_name: str,
) -> dict[str, Any]:

    log.info(
        "Starting Domoticz provisioning for "
        "%d vehicle(s)",
        len(vehicles),
    )

    state = (
        devices
        if isinstance(devices, dict)
        else {}
    )

    # ================================================================
    # Discovery
    # ================================================================

    discovery_available = True

    try:

        all_devices = await client.get_devices()

        log.info(
            "Domoticz returned %d visible device(s)",
            len(all_devices),
        )

    except DomoticzError as exc:

        discovery_available = False
        all_devices = []

        log.warning(
            "Could not query Domoticz devices: %s",
            exc,
        )

    # ================================================================
    # Hardware
    # ================================================================

    hardware_idx = await _discover_hardware_idx(
        client=client,
        state=state,
        all_devices=all_devices,
        hardware_name=hardware_name,
    )

    hardware_created = False

    if hardware_idx is None:

        log.info(
            "Domoticz hardware '%s' does not exist; "
            "creating it",
            hardware_name,
        )

        hardware_idx = await client.add_dummy_hardware(
            hardware_name
        )

        hardware_created = True

        log.info(
            "Created Domoticz Dummy hardware "
            "'%s' with IDX %d",
            hardware_name,
            hardware_idx,
        )

        if discovery_available:

            try:

                all_devices = await client.get_devices()

            except DomoticzError as exc:

                discovery_available = False

                log.warning(
                    "Could not refresh Domoticz devices "
                    "after hardware creation: %s",
                    exc,
                )

    else:

        log.info(
            "Reusing existing Domoticz Dummy hardware "
            "'%s' IDX %d",
            hardware_name,
            hardware_idx,
        )

    # ================================================================
    # Existing device inventory
    # ================================================================

    devices_for_hardware = [
        device
        for device in all_devices
        if _device_belongs_to_hardware(
            device,
            hardware_idx,
        )
    ]

    log.info(
        "Found %d existing device(s) on MySkoda "
        "hardware IDX %d",
        len(devices_for_hardware),
        hardware_idx,
    )

    # ================================================================
    # Reconciliation
    # ================================================================

    mapping: dict[
        str,
        dict[str, int]
    ] = {}

    total_created = 0
    total_reused = 0
    total_recovered = 0

    for vehicle in vehicles:

        vehicle_id = _vehicle_id(
            vehicle
        )

        vehicle_mapping: dict[
            str,
            int
        ] = {}

        stored_vehicle = state.get(
            vehicle_id,
            {},
        )

        if not isinstance(
            stored_vehicle,
            dict,
        ):
            stored_vehicle = {}

        vehicle_created = 0
        vehicle_reused = 0
        vehicle_recovered = 0

        log.info(
            "Reconciling vehicle %s",
            vehicle_id,
        )

        for key, definition in (
            DEVICE_DEFINITIONS.items()
        ):

            name = _vehicle_device_name(
                vehicle,
                definition,
            )

            # --------------------------------------------------------
            # Existing device by exact name
            # --------------------------------------------------------

            existing = _find_device_by_name(
                devices_for_hardware,
                name,
            )

            if existing is not None:

                idx = _safe_int(
                    existing.get("idx")
                )

                if idx is None:

                    log.warning(
                        "Ignoring device '%s' "
                        "because IDX is invalid",
                        name,
                    )

                else:

                    log.info(
                        "Reusing existing device "
                        "IDX %d: %s",
                        idx,
                        name,
                    )

                    try:

                        await _configure_device(
                            client=client,
                            idx=idx,
                            name=name,
                            definition=definition,
                        )

                    except DomoticzError as exc:

                        log.warning(
                            "Could not configure existing "
                            "device IDX %d '%s': %s",
                            idx,
                            name,
                            exc,
                        )

                    vehicle_mapping[key] = idx
                    vehicle_reused += 1
                    total_reused += 1

                    continue

            # --------------------------------------------------------
            # Persisted IDX
            # --------------------------------------------------------

            stored_idx = _safe_int(
                stored_vehicle.get(key)
            )

            if stored_idx is not None:

                persisted_device = (
                    _find_device_by_idx(
                        devices_for_hardware,
                        stored_idx,
                    )
                )

                if persisted_device is not None:

                    current_name = str(
                        persisted_device.get(
                            "Name",
                            "",
                        )
                    )

                    log.info(
                        "Recovering persisted device "
                        "IDX %d for '%s' "
                        "(current name: '%s')",
                        stored_idx,
                        name,
                        current_name,
                    )

                    try:

                        await _configure_device(
                            client=client,
                            idx=stored_idx,
                            name=name,
                            definition=definition,
                        )

                    except DomoticzError as exc:

                        log.warning(
                            "Could not reconfigure "
                            "recovered device IDX %d "
                            "'%s': %s",
                            stored_idx,
                            name,
                            exc,
                        )

                    vehicle_mapping[key] = (
                        stored_idx
                    )

                    vehicle_recovered += 1
                    total_recovered += 1

                    continue

                if not discovery_available:

                    log.warning(
                        "Cannot validate persisted "
                        "device IDX %d for '%s'; "
                        "device discovery unavailable. "
                        "Keeping persisted IDX.",
                        stored_idx,
                        name,
                    )

                    vehicle_mapping[key] = (
                        stored_idx
                    )

                    vehicle_recovered += 1
                    total_recovered += 1

                    continue

                log.warning(
                    "Persisted device IDX %d for "
                    "'%s' no longer exists on "
                    "MySkoda hardware",
                    stored_idx,
                    name,
                )

            # --------------------------------------------------------
            # Missing device
            # --------------------------------------------------------

            log.info(
                "Creating missing Domoticz device: %s",
                name,
            )

            idx = await client.create_virtual_sensor(
                hardware_idx=hardware_idx,
                sensor_name=name,
                sensor_type=int(
                    definition["sensor_type"]
                ),
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

            vehicle_created += 1
            total_created += 1

            # Add immediately to inventory.
            devices_for_hardware.append(
                {
                    "idx": idx,
                    "Name": name,
                    "HardwareID": hardware_idx,
                }
            )

        mapping[vehicle_id] = (
            vehicle_mapping
        )

        log.info(
            "Vehicle %s provisioning: "
            "reused=%d recovered=%d created=%d",
            vehicle_id,
            vehicle_reused,
            vehicle_recovered,
            vehicle_created,
        )

    # ================================================================
    # Persistent state
    # ================================================================

    result: dict[str, Any] = {
        "_hardware_idx": hardware_idx,
    }

    result.update(mapping)

    log.info(
        "Domoticz provisioning complete: "
        "vehicles=%d hardware_created=%s "
        "reused=%d recovered=%d created=%d",
        len(vehicles),
        hardware_created,
        total_reused,
        total_recovered,
        total_created,
    )

    return result
