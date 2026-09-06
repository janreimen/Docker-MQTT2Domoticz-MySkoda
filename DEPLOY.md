# Deploying Docker-MQTT2Domoticz-MySkoda (v0.1.4)

This assumes the layout already running on `hostname`:
`/srv/docker/Docker-MQTT2Domoticz-MySkoda/` with an `app/` subfolder
holding `config.py`, `domoticz_client.py`, `main.py`, `provisioner.py`,
`skoda_bridge.py`, `vehicles.py`.

## 1. Confirm `vehicles.csv` is in place

Path must match `VEHICLES_CSV_PATH` in your `.env`. Format:

```csv
id,name,vin
car_001,Octavia RS,TMBXXXXXXXXXXXX

`id` values must be unique; both `id` and `vin` are required per row —
`load_vehicles()` raises with the exact line number if either is
missing, so a bad CSV fails loudly at startup rather than silently.

## 2. Confirm `.env` has everything `config.py` actually requires

These four are hard requirements — the container won't start without
them (`required()` raises `RuntimeError` immediately):

```bash
grep -E '^(SKODA_USERNAME|SKODA_PASSWORD|DOMOTICZ_URL|DOMOTICZ_USER|DOMOTICZ_PASSWORD|MQTT_HOST|VEHICLES_CSV_PATH|DEVICES_JSON_PATH)=' .env
```

`DOMOTICZ_USER`/`DOMOTICZ_PASSWORD` are required in this codebase (not optional) — Domoticz web authentication must be enabled.

- `MQTT_PORT` defaults to `1883` — set it explicitly if your broker uses the non-default port confirmed elsewhere in this stack.
- `ENABLE_GPS` defaults to **`true`** in this codebase — set it to `false` explicitly in `.env` if you don't want vehicle position pushed to Domoticz.

## 3. Rebuild and restart

```bash
docker compose up -d --build --force-recreate
docker compose logs -f
```

## 4. What a healthy startup looks like

```
Starting Domoticz-MySkoda v0.1.4
Loaded N vehicle(s)
... myskoda.mqtt: Connected to MQTT
MySkoda connection ready
Automatic Domoticz provisioning enabled
Starting Domoticz provisioning for N vehicle(s)
Domoticz provisioning complete: vehicles=N hardware_created=... reused=... recovered=... created=...
Polling <vehicle_id> (<masked vin>)
Poll complete <vehicle_id>: locked=... range=... mileage=... inspection=...
```

If provisioning logs `reused=0 recovered=0 created=12` on every single
restart instead of settling into mostly `reused`, that means device
discovery or the persisted `devices.json` mapping isn't matching up —
check that `DEVICES_JSON_PATH` points to a path that actually persists
across container restarts (a bind mount, not an anonymous volume that
gets recreated).

## 5. Verify in Domoticz

**Setup → Devices** — look for `<name> [<id>] - <suffix>` entries per
vehicle. Values should update within one `POLL_INTERVAL_SECONDS` cycle.

Don't expect toggling any switch (Locked, Climatisation, Honk & Flash,
Window Heating, Wakeup) to do anything yet — see the README's "control
devices are provisioned but inert" section. That's expected behavior in
this version, not a deployment problem.

`devices.json` and `vehicles.csv` are untouched by a version rollback.
