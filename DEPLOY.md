# Deploy v0.1.1

```bash
sudo mkdir -p /srv/docker/Domoticz-MySkoda
cd /srv/docker/Domoticz-MySkoda
```

Copy the release here, then:

```bash
cp .env.example .env
nano .env
nano config/vehicles.csv
```

Use:

```text
DEVICES_JSON_PATH=/app/state/devices.json
DOMOTICZ_URL=http://ip:port
DOMOTICZ_PROVISION=true
DOMOTICZ_HARDWARE_NAME=MySkoda
```

Build/start:

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f --tail=200 domoticz-myskoda
```

The bridge will create a Dummy hardware `MySkoda`, then for each CSV vehicle create/reuse:

`Locked, Lights, Doors, Windows, Climatisation, Range, Mileage, Inspection, Position, Honk / Flash, Window Heating, Wakeup`

Range/Mileage are Custom Counter km; Inspection is Custom Counter days. IDX values are written to `state/devices.json`.

To add a third car, add it to `config/vehicles.csv` and restart:

```bash
docker compose restart
docker compose logs -f --tail=200 domoticz-myskoda
```

No manual IDX assignment is needed.

If provisioning gets HTTP 401, the Domoticz `skoda` account needs permission to perform the API commands used for hardware/device creation and updates.
