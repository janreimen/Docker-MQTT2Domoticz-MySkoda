from __future__ import annotations
import asyncio,json,logging
from pathlib import Path
import aiohttp
from myskoda import MySkoda
from config import load_config
from vehicles import load_vehicles,mask_vin
from domoticz_client import DomoticzClient
from skoda_bridge import SkodaBridge
VERSION='0.1.0'
async def update_vehicle(d,m,s,gps):
    for n,v in {'locked':s.locked,'lights_on':s.lights_on,'doors_open':s.doors_open,'windows_open':s.windows_open,'climatisation':s.ac_on}.items():
        if v is not None and n in m: await d.set_switch(int(m[n]),v)
    for n,v in {'range_km':s.range_km,'mileage_km':s.mileage_km,'inspection_due_days':s.inspection_due_days}.items():
        if v is not None and n in m: await d.set_custom_counter(int(m[n]),v)
    if gps and s.position and 'position' in m:
        lat,lon=s.position; await d.set_text(int(m['position']),f'{lat:.6f},{lon:.6f}')
async def main():
    c=load_config(); logging.basicConfig(level=getattr(logging,c.log_level,logging.INFO),format='%(asctime)s %(levelname)s %(name)s: %(message)s'); log=logging.getLogger('domoticz_myskoda')
    vs=load_vehicles(c.vehicles_csv_path); devices=json.loads(Path(c.devices_json_path).read_text())
    log.info('Starting Domoticz-MySkoda v%s',VERSION); log.info('Loaded %d vehicle(s)',len(vs))
    async with aiohttp.ClientSession() as session:
        myskoda=MySkoda(session,mqtt_enabled=True); await myskoda.connect(email=c.skoda_username,password=c.skoda_password); log.info('MySkoda connection ready')
        d=DomoticzClient(session,c.domoticz_url,c.domoticz_user,c.domoticz_password); bridges={v.vehicle_id:SkodaBridge(myskoda,v.vin,c.enable_gps) for v in vs}
        while True:
            for v in vs:
                try:
                    log.info('Polling %s (%s)',v.vehicle_id,mask_vin(v.vin)); s=await bridges[v.vehicle_id].snapshot(); await update_vehicle(d,devices[v.vehicle_id],s,c.enable_gps)
                    log.info('Poll complete %s: locked=%s range=%s mileage=%s',v.vehicle_id,s.locked,s.range_km,s.mileage_km)
                except Exception: log.exception('Polling failed for %s',v.vehicle_id)
            await asyncio.sleep(c.poll_interval_seconds)
if __name__=='__main__': asyncio.run(main())
