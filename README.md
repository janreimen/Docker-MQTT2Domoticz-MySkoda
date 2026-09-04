# Domoticz-MySkoda v0.1.1

Automatic MyŠkoda -> native Domoticz bridge.

## Automatic provisioning

On startup the bridge creates/reuses a Dummy hardware named `MySkoda` and creates 12 devices per configured vehicle. Device IDs are stored in `state/devices.json`, so restarts are idempotent. Adding a new row to `config/vehicles.csv` automatically provisions that car.

Range and Mileage are absolute Custom Counters in km. Inspection is an absolute Custom Counter in days. No incremental counter updates are used.

Set `DOMOTICZ_PROVISION=false` to disable provisioning.
