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
        timeout: int = 30,
    ) -> None:
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        # Retries are deliberately only used for value updates.
        # Creation/configuration requests remain single-shot to avoid
        # accidentally creating duplicate devices after a timeout.
        self.update_retries = 3
        self.update_retry_delay = 1.0

    # ================================================================
    # HTTP
    # ================================================================

    async def _request(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute one Domoticz API request.

        This method deliberately performs exactly one HTTP request.
        Higher-level update methods may retry safe value updates.
        """

        url = f"{self.base_url}/json.htm"

        log.debug(
            "Domoticz API request: %s",
            {
                key: value
                for key, value in params.items()
                if key != "password"
            },
        )

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

        except asyncio.TimeoutError as exc:
            raise DomoticzError(
                "Domoticz API request timed out"
            ) from exc

        except aiohttp.ClientError as exc:
            raise DomoticzError(
                f"Connection error: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise DomoticzError(
                "Domoticz returned a non-object JSON response"
            )

        status = data.get("status")

        if status not in (None, "OK"):
            raise DomoticzError(
                f"Domoticz API error: {data}"
            )

        log.debug(
            "Domoticz API response status=%s",
            data.get("status"),
        )

        return data

    async def _update_request(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a retryable Domoticz value update.

        This is intended for idempotent value updates such as:
        - switchlight
        - udevice

        It does not retry device creation or configuration requests.
        """

        for attempt in range(1, self.update_retries + 1):
            try:
                return await self._request(params)

            except DomoticzError as exc:
                if attempt >= self.update_retries:
                    raise

                delay = (
                    self.update_retry_delay
                    * attempt
                )

                log.warning(
                    "Domoticz update failed "
                    "(attempt %d/%d): %s; "
                    "retrying in %.1fs",
                    attempt,
                    self.update_retries,
                    exc,
                    delay,
                )

                await asyncio.sleep(delay)

        # Unreachable, but keeps type checkers happy.
        raise DomoticzError(
            "Domoticz update failed"
        )

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

        result = data.get("result", [])

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

        result = data.get("result", [])

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
            if str(item.get("Name", "")) == name:
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
            except (TypeError, ValueError):
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
            except (TypeError, ValueError):
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
                "mode1": "0",
                "mode2": "0",
                "mode3": "0",
                "mode4": "0",
                "mode5": "0",
                "mode6": "0",
            }
        )

        idx = data.get("idx")

        if idx is None:
            result = data.get("result")

            if isinstance(result, list) and result:
                first = result[0]

                if isinstance(first, dict):
                    idx = first.get("idx")

        try:
            return int(idx)
        except (TypeError, ValueError) as exc:
            raise DomoticzError(
                "Domoticz created hardware but "
                f"returned no valid IDX: {data}"
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
        """Create a virtual sensor device."""

        if sensor_name is None:
            sensor_name = name

        if not sensor_name:
            raise DomoticzError(
                "create_virtual_sensor requires sensor_name"
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

        data = await self._request(params)

        idx = self._extract_idx(data)

        if idx is not None:
            return idx

        return await self._find_created_idx(
            hardware_idx,
            sensor_name,
        )

    async def create_custom_sensor(
        self,
        hardware_idx: int,
        sensor_name: str,
        unit_label: str,
    ) -> int:
        """Create a genuine Domoticz General / Custom Sensor."""

        if not sensor_name:
            raise DomoticzError(
                "create_custom_sensor requires sensor_name"
            )

        if not unit_label:
            raise DomoticzError(
                "create_custom_sensor requires unit_label"
            )

        params: dict[str, Any] = {
            "type": "command",
            "param": "createdevice",
            "idx": str(hardware_idx),
            "sensorname": sensor_name,
            "sensormappedtype": "0xF31F",
            "sensoroptions": f"1;{unit_label}",
        }

        data = await self._request(params)

        idx = self._extract_idx(data)

        if idx is not None:
            return idx

        return await self._find_created_idx(
            hardware_idx,
            sensor_name,
        )

    @staticmethod
    def _extract_idx(
        data: dict[str, Any],
    ) -> int | None:
        idx = data.get("idx")

        if idx is None:
            result = data.get("result")

            if isinstance(result, list) and result:
                first = result[0]

                if isinstance(first, dict):
                    idx = first.get("idx")

        try:
            return int(idx)
        except (TypeError, ValueError):
            return None

    async def _find_created_idx(
        self,
        hardware_idx: int,
        sensor_name: str,
    ) -> int:
        """Find a newly created device by exact name."""

        devices = await self.get_devices_by_hardware(
            hardware_idx
        )

        for device in devices:
            if str(device.get("Name", "")) != sensor_name:
                continue

            try:
                return int(device.get("idx"))
            except (TypeError, ValueError):
                continue

        raise DomoticzError(
            f"Domoticz created sensor '{sensor_name}' "
            "but its IDX could not be determined"
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
            params["switchtype"] = str(switch_type)

        await self._request(params)

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
        """Configure an existing RFXMeter-style counter."""

        switch_type = (
            5
            if quantity.lower() == "time"
            else 3
        )

        await self.set_device(
            idx=idx,
            name=name,
            used=1,
            switch_type=switch_type,
        )

    async def configure_custom_sensor(
        self,
        idx: int,
        name: str,
    ) -> None:
        """Rename an existing Custom Sensor device."""

        await self.set_device(
            idx=idx,
            name=name,
            used=1,
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
    # Device value updates
    # ================================================================

    async def set_switch(
        self,
        idx: int,
        value: bool,
    ) -> None:
        switchcmd = "On" if value else "Off"

        log.debug(
            "Setting Domoticz switch IDX %d -> %s",
            idx,
            switchcmd,
        )

        await self._update_request(
            {
                "type": "command",
                "param": "switchlight",
                "idx": str(idx),
                "switchcmd": switchcmd,
            }
        )

    async def set_custom_counter(
        self,
        idx: int,
        value: int | float,
    ) -> None:
        """Push a value to an RFXMeter-style counter."""

        value_text = str(value)

        log.debug(
            "Setting Domoticz custom counter "
            "IDX %d -> %s",
            idx,
            value_text,
        )

        await self._update_request(
            {
                "type": "command",
                "param": "udevice",
                "idx": str(idx),
                "nvalue": "0",
                "svalue": value_text,
            }
        )

    async def set_custom_sensor(
        self,
        idx: int,
        value: int | float,
    ) -> None:
        """Push an absolute value to a Custom Sensor."""

        value_text = str(value)

        log.debug(
            "Setting Domoticz custom sensor "
            "IDX %d -> %s",
            idx,
            value_text,
        )

        await self._update_request(
            {
                "type": "command",
                "param": "udevice",
                "idx": str(idx),
                "nvalue": "0",
                "svalue": value_text,
            }
        )

    async def set_text(
        self,
        idx: int,
        value: str,
    ) -> None:
        log.debug(
            "Setting Domoticz text IDX %d -> %s",
            idx,
            value,
        )

        await self._update_request(
            {
                "type": "command",
                "param": "udevice",
                "idx": str(idx),
                "nvalue": "0",
                "svalue": value,
            }
        )

