from __future__ import annotations
import csv
from dataclasses import dataclass
@dataclass(frozen=True)
class VehicleConfig:
    vehicle_id:str; name:str; vin:str
def mask_vin(vin): return '*'*max(0,len(vin)-6)+vin[-6:]
def load_vehicles(path):
    with open(path,encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    if not rows or not {'id','name','vin'}.issubset(rows[0]): raise RuntimeError(f'{path} must contain id,name,vin')
    out=[VehicleConfig(r['id'].strip(),r.get('name','').strip() or r['id'].strip(),r['vin'].strip()) for r in rows if r.get('id','').strip() and r.get('vin','').strip()]
    if not out: raise RuntimeError(f'No vehicles found in {path}')
    return out
