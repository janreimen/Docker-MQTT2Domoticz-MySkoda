from __future__ import annotations
import logging, aiohttp
log=logging.getLogger(__name__)
class DomoticzClient:
    def __init__(self,session,base_url,username=None,password=None):
        self.session=session; self.base_url=base_url.rstrip('/'); self.auth=aiohttp.BasicAuth(username,password) if username and password else None
    async def update_device(self,idx,nvalue=0,svalue=''):
        params={'type':'command','param':'udevice','idx':str(idx),'nvalue':str(nvalue),'svalue':str(svalue)}
        try:
            async with self.session.get(f'{self.base_url}/json.htm',params=params,auth=self.auth,timeout=aiohttp.ClientTimeout(total=10)) as r:
                body=await r.text()
                if r.status!=200: log.error('Domoticz HTTP %s idx=%s: %s',r.status,idx,body[:300]); return False
                try: data=await r.json(content_type=None)
                except Exception: log.error('Domoticz non-JSON idx=%s: %s',idx,body[:300]); return False
                if data.get('status')!='OK': log.error('Domoticz rejected idx=%s: %s',idx,data); return False
                return True
        except Exception: log.exception('Domoticz update failed idx=%s',idx); return False
    async def set_switch(self,idx,value): return await self.update_device(idx,1 if value else 0,'0')
    async def set_text(self,idx,text): return await self.update_device(idx,0,text)
    async def set_custom_counter(self,idx,value): return await self.update_device(idx,0,value)
