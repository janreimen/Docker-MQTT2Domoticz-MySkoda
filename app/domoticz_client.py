from __future__ import annotations
import logging,json,aiohttp,base64
log=logging.getLogger(__name__)
class DomoticzClient:
 def __init__(self,session,base_url,username=None,password=None): self.s=session; self.base=base_url.rstrip("/"); self.auth=aiohttp.BasicAuth(username,password) if username and password else None
 async def request(self,p):
  try:
   async with self.s.get(f"{self.base}/json.htm",params=p,auth=self.auth,timeout=aiohttp.ClientTimeout(total=15)) as r:
    body=await r.text()
    try: data=json.loads(body)
    except: data={}
    if r.status!=200 or (data and data.get("status") not in ("OK",None)): log.error("Domoticz HTTP %s: %s",r.status,body[:500]); return None
    return data
  except Exception: log.exception("Domoticz request failed"); return None
 async def get_hardware(self): return await self.request({"type":"command","param":"gethardware"})
 async def get_devices(self): return await self.request({"type":"command","param":"getdevices","filter":"all","used":"false","order":"Name"})
 async def add_dummy_hardware(self,name): return await self.request({"type":"command","param":"addhardware","htype":"15","port":"1","name":name,"enabled":"true"})
 async def create_virtual_sensor(self,hwidx,name,sensortype): return await self.request({"type":"command","param":"createvirtualsensor","idx":str(hwidx),"sensorname":name,"sensortype":str(sensortype)})
 async def setused(self,idx,name,switchtype=None,options=None):
  p={"type":"command","param":"setused","idx":str(idx),"name":name,"used":"true"}
  if switchtype is not None:p["switchtype"]=str(switchtype)
  if options:p["options"]=base64.b64encode(";".join(f"{k}:{v}" for k,v in options.items()).encode()).decode()
  return await self.request(p)
 async def update_device(self,idx,nvalue=0,svalue=""): return await self.request({"type":"command","param":"udevice","idx":str(idx),"nvalue":str(nvalue),"svalue":str(svalue)})
 async def set_switch(self,idx,v): return await self.update_device(idx,1 if v else 0,"0")
 async def set_text(self,idx,v): return await self.update_device(idx,0,v)
 async def set_custom_counter(self,idx,v): return await self.update_device(idx,0,v)
