from __future__ import annotations
import os
from dataclasses import dataclass
@dataclass(frozen=True)
class Config:
 skoda_username:str; skoda_password:str; skoda_spin:str|None; domoticz_url:str; domoticz_user:str; domoticz_password:str; mqtt_host:str; mqtt_port:int; mqtt_username:str|None; mqtt_password:str|None; mqtt_domoticz_out_topic:str; poll_interval_seconds:int; enable_gps:bool; skoda_ac_temperature:float; vehicles_csv_path:str; devices_json_path:str; log_level:str; domoticz_provision:bool; domoticz_hardware_name:str
def e(n,d=None):
 v=os.getenv(n,d); return v.strip() if v is not None else None
def req(n):
 v=e(n)
 if not v: raise RuntimeError(f"Missing required environment variable: {n}")
 return v
def b(n,d):
 v=e(n); return d if v is None else v.lower() in {"1","true","yes","on"}
def load_config():
 return Config(req("SKODA_USERNAME"),req("SKODA_PASSWORD"),e("SKODA_SPIN") or None,req("DOMOTICZ_URL").rstrip("/"),req("DOMOTICZ_USER"),req("DOMOTICZ_PASSWORD"),req("MQTT_HOST"),int(e("MQTT_PORT","1883")),e("MQTT_USERNAME") or None,e("MQTT_PASSWORD") or None,e("MQTT_DOMOTICZ_OUT_TOPIC","skoda/out"),int(e("POLL_INTERVAL_SECONDS","1800")),b("ENABLE_GPS",True),float(e("SKODA_AC_TEMPERATURE","21.0")),req("VEHICLES_CSV_PATH"),req("DEVICES_JSON_PATH"),e("LOG_LEVEL","INFO").upper(),b("DOMOTICZ_PROVISION",True),e("DOMOTICZ_HARDWARE_NAME","MySkoda"))
