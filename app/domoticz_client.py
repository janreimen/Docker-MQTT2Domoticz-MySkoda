import base64
import logging
from typing import Any, Optional

import aiohttp


log = logging.getLogger(__name__)


class DomoticzError(RuntimeError):
    """Raised when the Domoticz API request fails."""


class DomoticzClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        password: str,
        timeout: int = 10,
    ):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/json.htm"

        try:
            async with self.session.get(
                url,
                params=params,
                auth=aiohttp.BasicAuth(
                    self.username,
                    self.password,
                ),
                timeout=aiohttp.ClientTimeout(
                    total=self.timeout
                ),
            ) as resp:

                text = await resp.text()

                if resp.status != 200:
                    raise DomoticzError(
                        f"HTTP {resp.status}: {text[:500]}"
                    )

                try:
                    data = await resp.json(
                        content_type=None
                    )
                except Exception as exc:
                    raise DomoticzError(
                        f"Invalid JSON from Domoticz: "
                        f"{text[:500]}"
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

        return data

    # ==============================================================
    # Discovery
    # ==============================================================

    async def get_hardware(self) -> list[dict[str, Any]]:
        """Return all Domoticz hardware visible to this user."""

        data = await self._request(
            {
                "type": "hardware",
            }
        )

        result = data.get("result", [])

        if not isinstance(result, list):
            return []

        return result

    async def get_hardware_by_name(
        self,
        name: str,
    ) -> Optional[dict[str, Any]]:
        """Find hardware by exact name."""

        hardware = await self.get_hardware()

        for item in hardware:
            if str(item.get("Name", "")) == name:
                return item

        return None

    async def get_devices(self) -> list[dict[str, Any]]:
        """Return all Domoticz devices visible to this user."""

        data = await self._request(
            {
                "type": "devices",
                "filter": "all",
                "used": "true",
            }
        )

        result = data.get("result", [])

        if not isinstance(result, list):
            return []

        return result

    async def get_devices_by_hardware(
        self,
        hardware_idx: int,
    ) -> list[dict[str, Any]]:
        """Return devices belonging to one hardware IDX."""

        devices = await self.get_devices()

        return [
            device
            for device in devices
            if int(device.get("HardwareID", -1))
            == int(hardware_idx)
        ]

    # ==============================================================
    # Hardware
    # ==============================================================

    async def add_dummy_hardware(
        self,
        name: str,
    ) -> int:
        """
        Create a Dummy hardware.

        This should only be reached when the hardware really does not
        already exist.
        """

        log.info(
            "Creating Domoticz Dummy hardware '%s'",
            name,
        )

        data = await self._request(
            {
                "type": "command",
                "param": "addhardware",
                "htype": "15",
                "port": "1",
                "name": name,
                "enabled": "true",
            }
        )

        # Different Domoticz versions may return the IDX differently.
        if data.get("idx") is not None:
            return int(data["idx"])

        result = data.get("result")

        if isinstance(result, dict):
            if result.get("idx") is not None:
                return int(result["idx"])

        # Final fallback: rediscover it.
        hardware = await self.get_hardware_by_name(name)

        if hardware is not None:
            return int(hardware["idx"])

        raise DomoticzError(
            f"Created hardware '{name}' but could not determine IDX"
        )

    # ==============================================================
    # Virtual sensors
    # ==============================================================

    async def create_virtual_sensor(
        self,
        hardware_idx: int,
        sensor_name: str,
        sensor_type: int,
    ) -> int:
        """Create a Domoticz virtual sensor."""

        log.info(
            "Creating Domoticz virtual sensor '%s' "
            "on HW %d",
            sensor_name,
            hardware_idx,
        )

        data = await self._request(
            {
                "type": "command",
                "param": "createvirtualsensor",
                "idx": str(hardware_idx),
                "sensorname": sensor_name,
                "sensortype": str(sensor_type),
            }
        )

        if data.get("idx") is not None:
            return int(data["idx"])

        result = data.get("result")

        if isinstance(result, dict):
            if result.get("idx") is not None:
                return int(result["idx"])

        # Discover by exact name.
        devices = await self.get_devices_by_hardware(
            hardware_idx
        )

        for device in devices:
            if str(device.get("Name", "")) == sensor_name:
                return int(device["idx"])

        raise DomoticzError(
            f"Created sensor '{sensor_name}' but "
            f"could not determine IDX"
        )

    # ==============================================================
    # Device configuration
    # ==============================================================

    async def set_used(
        self,
        idx: int,
        name: str,
        switch_type: Optional[int] = None,
        options: Optional[str] = None,
    ) -> None:
        """
        Configure an existing Domoticz device.

        Domoticz expects Options as Base64.
        """

        params: dict[str, Any] = {
            "type": "command",
            "param": "setused",
            "idx": str(idx),
            "name": name,
            "used": "true",
        }

        if switch_type is not None:
            params["switchtype"] = str(switch_type)

        if options is not None:
            encoded = base64.b64encode(
                options.encode("utf-8")
            ).decode("ascii")

            params["options"] = encoded

        await self._request(params)

    async def configure_switch(
        self,
        idx: int,
        name: str,
        switch_type: int,
    ) -> None:
        await self.set_used(
            idx=idx,
            name=name,
            switch_type=switch_type,
        )

    async def configure_custom_counter(
        self,
        idx: int,
        name: str,
        quantity: str,
        units: str,
    ) -> None:
        """
        Configure RFXMeter as Custom Counter.

        switchtype=3 = Custom Counter
        """

        options = (
            f"ValueQuantity:{quantity};"
            f"ValueUnits:{units}"
        )

        await self.set_used(
            idx=idx,
            name=name,
            switch_type=3,
            options=options,
        )

    async def configure_text(
        self,
        idx: int,
        name: str,
    ) -> None:
        await self.set_used(
            idx=idx,
            name=name,
        )

    # ==============================================================
    # Updates
    # ==============================================================

    async def update_device(
        self,
        idx: int,
        nvalue: int = 0,
        svalue: str = "",
    ) -> None:
        """Update a Domoticz device using udevice."""

        try:
            await self._request(
                {
                    "type": "command",
                    "param": "udevice",
                    "idx": str(idx),
                    "nvalue": str(nvalue),
                    "svalue": str(svalue),
                }
            )

        except Exception:
            log.exception(
                "Failed to update Domoticz device idx %s",
                idx,
            )
            raise

    async def set_switch(
        self,
        idx: int,
        state: bool,
    ) -> None:
        """Set a virtual switch On or Off."""

        await self._request(
            {
                "type": "command",
                "param": "switchlight",
                "idx": str(idx),
                "switchcmd": (
                    "On" if state else "Off"
                ),
            }
        )

    async def set_custom_counter(
        self,
        idx: int,
        value: int | float,
    ) -> None:
        """
        Set an ABSOLUTE Custom Counter value.

        This sends the complete current value.
        It does NOT increment the existing counter.
        """

        await self.update_device(
            idx=idx,
            nvalue=0,
            svalue=str(value),
        )

    async def set_text(
        self,
        idx: int,
        value: str,
    ) -> None:
        """Set a Domoticz text device."""

        await self.update_device(
            idx=idx,
            nvalue=0,
            svalue=value,
        )

