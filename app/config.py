from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    skoda_username: str
    skoda_password: str
    skoda_spin: str | None

    domoticz_url: str
    domoticz_user: str
    domoticz_password: str

    mqtt_host: str
    mqtt_port: int
    mqtt_username: str | None
    mqtt_password: str | None
    mqtt_domoticz_out_topic: str

    poll_interval_seconds: int
    enable_gps: bool
    skoda_ac_temperature: float

    vehicles_csv_path: str
    devices_json_path: str

    str
    log_level: str

    domoticz_provision: bool
    domoticz_hardware_name: str


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)

    if value is None:
        return None

    return value.strip()


def required(name: str) -> str:
    value = env(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


def boolean(name: str, default: bool) -> bool:
    value = env(name)

    if value is None:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def load_config() -> Config:
    return Config(
        skoda_username=required("SKODA_USERNAME"),
        skoda_password=required("SKODA_PASSWORD"),
        skoda_spin=env("SKODA_SPIN") or None,

        domoticz_url=required("DOMOTICZ_URL").rstrip("/"),
        domoticz_user=required("DOMOTICZ_USER"),
        domoticz_password=required("DOMOTICZ_PASSWORD"),

        mqtt_host=required("MQTT_HOST"),
        mqtt_port=int(env("MQTT_PORT", "1883")),
        mqtt_username=env("MQTT_USERNAME") or None,
        mqtt_password=env("MQTT_PASSWORD") or None,
        mqtt_domoticz_out_topic=env(
            "MQTT_DOMOTICZ_OUT_TOPIC",
            "skoda/out",
        ),

        poll_interval_seconds=int(
            env("POLL_INTERVAL_SECONDS", "1800")
        ),

        enable_gps=boolean("ENABLE_GPS", True),

        skoda_ac_temperature=float(
            env("SKODA_AC_TEMPERATURE", "21.0")
        ),

        vehicles_csv_path=required("VEHICLES_CSV_PATH"),
        devices_json_path=required("DEVICES_JSON_PATH"),

        log_level=env("LOG_LEVEL", "INFO").upper(),

        domoticz_provision=boolean(
            "DOMOTICZ_PROVISION",
            True,
        ),

        domoticz_hardware_name=env(
            "DOMOTICZ_HARDWARE_NAME",
            "MySkoda",
        ),
    )
