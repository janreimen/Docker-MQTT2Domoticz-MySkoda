from __future__ import annotations
import logging, asyncio
from dataclasses import dataclass
log=logging.getLogger(__name__)
@dataclass
class VehicleSnapshot:
    locked:bool|None=None; lights_on:bool|None=None; doors_open:bool|None=None; windows_open:bool|None=None; ac_on:bool|None=None
    range_km:int|None=None; mileage_km:int|None=None; inspection_due_days:int|None=None; position:tuple[float,float]|None=None
def dump(x):
    if x is None:return None
    if hasattr(x,'model_dump'):
        try:return x.model_dump()
        except Exception:pass
    if hasattr(x,'__dict__'):
        try:return {k:dump(v) for k,v in vars(x).items() if not k.startswith('_')}
        except Exception:pass
    if isinstance(x,dict):return {k:dump(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [dump(v) for v in x]
    return x
def find(x,names):
    x=dump(x)
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower().replace('-','_') in names:return v
        for v in x.values():
            z=find(v,names)
            if z is not None:return z
    elif isinstance(x,list):
        for v in x:
            z=find(v,names)
            if z is not None:return z
    return None
def truth(x):
    if isinstance(x,bool):return x
    if x is None:return None
    s=str(x).lower()
    if 'unlocked' in s or 'open' in s or 'true' in s or ' on' in s:return True
    if 'locked' in s or 'closed' in s or 'false' in s or 'off' in s:return False
    return None
def num(x):
    try:return int(float(str(x).replace(',','.')))
    except Exception:return None
class SkodaBridge:
    def __init__(self,myskoda,vin,enable_gps=True):self.myskoda=myskoda; self.vin=vin; self.enable_gps=enable_gps
    async def snapshot(self):
        status,drange,health,maintenance,ac=await asyncio.gather(
            self.myskoda.get_status(self.vin),self.myskoda.get_driving_range(self.vin),self.myskoda.get_health(self.vin),
            self.myskoda.get_maintenance(self.vin),self.myskoda.get_air_conditioning(self.vin))
        positions=await self.myskoda.get_positions(self.vin) if self.enable_gps else None
        p=dump(positions); pos=None
        if isinstance(p,dict):
            for item in p.get('positions',[]):
                gps=item.get('gps_coordinates',{}) if isinstance(item,dict) else {}
                if gps.get('latitude') is not None and gps.get('longitude') is not None: pos=(float(gps['latitude']),float(gps['longitude'])); break
        return VehicleSnapshot(
            locked=truth(find(status,{'doors_locked','locked'})),lights_on=truth(find(status,{'lights_on','lights'})),
            doors_open=truth(find(status,{'doors_open','door_open'})),windows_open=truth(find(status,{'windows_open','window_open'})),
            ac_on=truth(find(ac,{'state','ac_on','air_conditioning_on'})),
            range_km=num(find(drange,{'total_range_in_km','range_in_km','total_range'})),
            mileage_km=num(find(health,{'mileage_in_km','mileage','odometer'})),
            inspection_due_days=num(find(maintenance,{'inspection_due_in_days'})),position=pos)
