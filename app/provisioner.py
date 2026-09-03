from __future__ import annotations
import logging
log=logging.getLogger(__name__)
DEVICES={"locked":("Locked","switch"),"lights_on":("Lights","switch"),"doors_open":("Doors","switch"),"windows_open":("Windows","switch"),"climatisation":("Climatisation","switch"),"range_km":("Range","counter_km"),"mileage_km":("Mileage","counter_km"),"inspection_due_days":("Inspection","counter_days"),"position":("Position","text"),"honk_flash":("Honk / Flash","switch"),"window_heating":("Window Heating","switch"),"wakeup":("Wakeup","switch")}
async def _devices(c): return ((await c.get_devices()) or {}).get("result",[]) or []
async def provision(c,vehicles,mapping,hardware_name):
    hw=((await c.get_hardware()) or {}).get("result",[]) or []
    d=next((x for x in hw if str(x.get("Type"))=="15" and x.get("Name")==hardware_name),None)
    if d is None:
        log.info("Creating Dummy hardware '%s'",hardware_name); await c.add_dummy_hardware(hardware_name)
        hw=((await c.get_hardware()) or {}).get("result",[]) or []; d=next((x for x in hw if str(x.get("Type"))=="15" and x.get("Name")==hardware_name),None)
    if d is None: raise RuntimeError(f"Cannot find Dummy hardware '{hardware_name}'")
    hwidx=int(d["idx"]); existing=await _devices(c); byname={x.get("Name"):x for x in existing}
    for v in vehicles:
        vm=mapping.setdefault(v.vehicle_id,{})
        for key,(suffix,kind) in DEVICES.items():
            name=f"{v.name} [{v.vehicle_id}] - {suffix}"
            if vm.get(key): continue
            if name in byname: vm[key]=int(byname[name]["idx"]); continue
            st=113 if kind.startswith("counter") else 31 if kind=="text" else 1
            r=await c.create_virtual_sensor(hwidx,name,st); idx=(r or {}).get("idx")
            if idx is None:
                fresh=await _devices(c); hit=next((x for x in fresh if x.get("Name")==name),None); idx=hit.get("idx") if hit else None
            if idx is None: raise RuntimeError(f"Could not create '{name}'")
            idx=int(idx)
            if kind.startswith("counter"):
                await c.setused(idx,name,switchtype=3,options={"ValueQuantity":"Custom","ValueUnits":"days" if kind=="counter_days" else "km"})
            vm[key]=idx; byname[name]={"Name":name,"idx":idx}
    return mapping
