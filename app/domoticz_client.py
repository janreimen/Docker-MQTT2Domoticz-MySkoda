from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp


log = logging.getLogger("domoticz")


class DomoticzError(Exception):
    """Raised when the Domoticz API returns an error."""


class DomoticzClient:

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str = "",
        password: str = "",
        timeout: int = 15,
    ) -> None:
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = aiohttp.ClientTimeout(
            total=timeout
        )

    # ================================================================
    # HTTP
    # ================================================================

    async def _request(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:

        url = f"{self.base_url}/json.htm"

        auth = None

        if self.username or self.password:
            auth = aiohttp.BasicAuth(
                self.username,
                self.password,
            )

        try:
            async with self.session.get(
                url,
                params=params,
                auth=auth,
                timeout=self.timeout,
            ) as response:

                text = await response.text()

                if response.status != 200:
                    raise DomoticzError(
                        f"HTTP {response.status}: {text}"
                    )

                try:
                    data = await response.json(
                        content_type=None
                    )
                except Exception as exc:
                    raise DomoticzError(
                        f"Invalid JSON response: {text}"
                    ) from exc

        except asyncio.CancelledError:
            raise

        except aiohttp.ClientError as exc:
            raise DomoticzError(
                f"Connection error: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise DomoticzError(
                "Domoticz returned a "
                "non-object JSON response"
            )

        status = data.get("status")

        if status not in (
            None,
            "OK",
        ):
            raise DomoticzError(
                f"Domoticz API error: {data}"
            )

        return data

    # ================================================================
    # Discovery
    # ================================================================

    async def get_devices(
        self,
    ) -> list[dict[str, Any]]:

        data = await self._request(
            {
                "type": "command",
                "param": "getdevices",
                "filter": "all",
                "used": "true",
            }
        )

        result = data.get(
            "result",
            [],
        )

        if not isinstance(result, list):
            return []

        return [
            item
            for item in result
            if isinstance(item, dict)
        ]

    async def get_hardware(
        self,
    ) -> list[dict[str, Any]]:

        data = await self._request(
            {
                "type": "command",
                "param": "gethardware",
            }
        )

        result = data.get(
            "result",
            [],
        )

        if not isinstance(result, list):
            return []

        return [
            item
            for item in result
            if isinstance(item, dict)
        ]

    async def get_hardware_by_name(
        self,
        name: str,
    ) -> dict[str, Any] | None:

        hardware = await self.get_hardware()

        for item in hardware:
            if str(
                item.get("Name", "")
            ) == name:
                return item

        return None

    async def get_devices_by_hardware(
        self,
        hardware_idx: int,
    ) -> list[dict[str, Any]]:

        devices = await self.get_devices()

        result: list[dict[str, Any]] = []

        for device in devices:
            try:
                device_hardware = int(
                    device.get("HardwareID")
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if device_hardware == hardware_idx:
                result.append(device)

        return result

    async def get_device(
        self,
        idx: int,
    ) -> dict[str, Any] | None:

        devices = await self.get_devices()

        for device in devices:
            try:
                device_idx = int(
                    device.get("idx")
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if device_idx == idx:
                return device

        return None

    # ================================================================
    # Hardware creation
    # ================================================================

    async def add_dummy_hardware(
        self,
        name: str,
    ) -> int:

        data = await self._request(
            {
                "type": "command",
                "param": "addhardware",
                "htype": "15",
                "port": "0",
                "name": name,
                "enabled": "true",
                "datatimeout": "0",
            }
        )

        idx = data.get("idx")

        if idx is None:
            result = data.get(
                "result"
            )

            if (
                isinstance(result, list)
                and result
            ):
                first = result[0]

                if isinstance(first, dict):
                    idx = first.get("idx")

        try:
            return int(idx)
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise DomoticzError(
                "Domoticz created hardware "
                "but returned no valid IDX: "
                f"{data}"
            ) from exc

    # ================================================================
    # Virtual sensor creation
    # ================================================================

    async def create_virtual_sensor(
        self,
        hardware_idx: int,
        sensor_name: str | None = None,
        sensor_type: int = 0,
        switch_type: int = 0,
        options: str = "",
        name: str | None = None,
    ) -> int:

        if sensor_name is None:
            sensor_name = name

        if not sensor_name:
            raise DomoticzError(
                "create_virtual_sensor requires "
                "sensor_name"
            )

        params: dict[str, Any] = {
            "type": "command",
            "param": "createvirtualsensor",
            "idx": str(hardware_idx),
            "sensorname": sensor_name,
            "sensortype": str(sensor_type),
            "switchtype": str(switch_type),
        }

        if options:
            params["options"] = options

        data = await self._request(
            params
        )

        idx = data.get("idx")

        if idx is None:
            result = data.get(
                "result"
            )

            if (
                isinstance(result, list)
                and result
            ):
                first = result[0]

                if isinstance(first, dict):
                    idx = first.get("idx")

        if idx is not None:
            try:
                return int(idx)
            except (
                TypeError,
                ValueError,
            ):
                pass

        devices = await self.get_devices_by_hardware(
            hardware_idx
        )

        for device in devices:
            if str(
                device.get("Name", "")
            ) == sensor_name:
                try:
                    return int(
                        device.get("idx")
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

        raise DomoticzError(
            "Domoticz created sensor but "
            "its IDX could not be determined: "
            f"{data}"
        )

    # ================================================================
    # Device configuration
    # ================================================================

    async def set_device(
        self,
        idx: int,
        name: str,
        used: int = 1,
        switch_type: int | None = None,
    ) -> None:

        params: dict[str, Any] = {
            "type": "command",
            "param": "setused",
            "idx": str(idx),
            "name": name,
            "used": "true" if used else "false",
        }

        if switch_type is not None:
            params["switchtype"] = str(
                switch_type
            )

        await self._request(
            params
        )

    async def update_device_name(
        self,
        idx: int,
        name: str,
    ) -> None:

        await self.set_device(
            idx=idx,
            name=name,
            used=1,
        )

    async def configure_switch(
        self,
        idx: int,
        name: str,
        switch_type: int,
    ) -> None:

        await self.set_device(
            idx=idx,
            name=name,
            used=1,
            switch_type=switch_type,
        )

    async def configure_custom_counter(
        self,
        idx: int,
        name: str,
        quantity: str,
        units: str,
    ) -> None:

        if quantity.lower() == "time":
            switch_type = 5
        else:
            switch_type = 3

        await self.set_device(
            idx=idx,
            name=name,
            used=1,
            switch_type=switch_type,
        )

    async def configure_text(
        self,
        idx: int,
        name: str,
    ) -> None:

        await self.set_device(
            idx=idx,
            name=name,
            used=1,
        )

    # ================================================================
    # Device updates
    # ================================================================

    async def set_switch(
        self,
        idx: int,
        value: bool,
    ) -> None:

        await self._request(
            {
                "type": "command",
                "param": "switchlight",
                "idx": str(idx),
                "switchcmd": (
                    "On"
                    if value
                    else "Off"
                ),
            }
        )

    async def set_custom_counter(
        self,
        idx: int,
        value: int | float,
    ) -> None:

        await self._request(
            {
                "type": "command",
                "param": "udevice",
                "idx": str(idx),
                "nvalue": "0",
                "svalue": str(value),
            }
        )

    async def set_text(
        self,
        idx: int,
        value: str,
    ) -> None:

        await self._request(
            {
                "type": "command",
                "param": "udevice",
                "idx": str(idx),
                "nvalue": "0",
                "svalue": value,
            }
        )
