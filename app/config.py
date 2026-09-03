from __future__ import annotations
import os
from dataclasses import dataclass
@dataclass(frozen=True)
class Config:
    skoda_username:str; skoda_password:str; skoda_spin:str|None
    domoticz_url:str; domoticz_user:str; domoticz_password:str
    mqtt_host:str; mqtt_port:int; mqtt_username:str|None; mqtt_password:str|None
    mqtt_domoticz_out_topic:str; poll_interval_seconds:int; enable_gps:bool
    skoda_ac_temperature:float; vehicles_csv_path:str; devices_json_path:str; log_level:str
def _env(n,d=None):
    v=os.getenv(n,d); return v.strip() if v is not None else None
def _req(n):
    v=_env(n)
    if not v: raise RuntimeError(f'Missing required environment variable: {n}')
    return v
def _bool(n,d):
    v=_env(n); return d if v is None else v.lower() in {'1','true','yes','on'}
def load_config():
    return Config(_req('SKODA_USERNAME'),_req('SKODA_PASSWORD'),_env('SKODA_SPIN') or None,
      _req('DOMOTICZ_URL').rstrip('/'),_req('DOMOTICZ_USER'),_req('DOMOTICZ_PASSWORD'),
      _req('MQTT_HOST'),int(_env('MQTT_PORT','1883')),_env('MQTT_USERNAME') or None,_env('MQTT_PASSWORD') or None,
      _env('MQTT_DOMOTICZ_OUT_TOPIC','skoda/out'),int(_env('POLL_INTERVAL_SECONDS','1800')),
      _bool('ENABLE_GPS',True),float(_env('SKODA_AC_TEMPERATURE','21.0')),
      _req('VEHICLES_CSV_PATH'),_req('DEVICES_JSON_PATH'),_env('LOG_LEVEL','INFO').upper())
