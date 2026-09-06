# Docker-MQTT2Domoticz-MySkoda

Polls one or more MySkoda-connected vehicles and pushes their state into
auto-provisioned Domoticz virtual devices. Runs as a single long-lived
Docker container.

**Version: 0.1.4**

## How it works

On startup, the container:

1. Loads vehicles from a CSV file (`VEHICLES_CSV_PATH`) — one row per
   vehicle, columns `id,name,vin`.
2. Connects to MySkoda (`myskoda` library, MQTT-enabled session to the
   Skoda cloud — unrelated to your own Domoticz MQTT broker).
3. If `DOMOTICZ_PROVISION=true` (default), reconciles Domoticz devices
   for every vehicle: reuses existing devices by exact name match, falls
   back to a persisted idx mapping (`DEVICES_JSON_PATH`) if discovery is
   restricted, and only creates what's genuinely missing. The mapping is
   written back to `DEVICES_JSON_PATH` atomically (temp file + `fsync` +
   `os.replace`) after every provisioning pass.
4. Enters a poll loop: every `POLL_INTERVAL_SECONDS`, fetches a snapshot
   per vehicle and pushes it into that vehicle's Domoticz devices via
   Domoticz's HTTP JSON API (`/json.htm`).

## Devices provisioned per vehicle

Named `<vehicle name> [<vehicle id>] - <suffix>` under one shared Dummy
hardware entry (name set by `DOMOTICZ_HARDWARE_NAME`, default `MySkoda`).

| Key | Suffix | Kind | Currently driven by the poll loop? |
|---|---|---|---|
| `locked` | Locked | Switch | Yes (read) |
| `lights_on` | Lights | Switch | Yes (read) |
| `doors_open` | Doors | Switch | Yes (read) |
| `windows_open` | Windows | Switch | Yes (read) |
| `climatisation` | Climatisation | Switch | Yes (read) |
| `range_km` | Range | Custom counter (km) | Yes |
| `mileage_km` | Mileage | Custom counter (km) | Yes |
| `inspection_due_days` | Inspection | Custom counter (days) | Yes |
| `position` | Position | Text | Yes, only if `ENABLE_GPS=true` |
| `honk_flash` | Honk / Flash | Switch | **No — see limitation below** |
| `window_heating` | Window Heating | Switch | **No — see limitation below** |
| `wakeup` | Wakeup | Switch | **No — see limitation below** |

## ROADMAP 

`provisioner.py` creates the `honk_flash`, `window_heating`, and `wakeup`
switches (and `locked`/`climatisation` are writable in principle), but
based on the actual code in `main.py`, `domoticz_client.py`, and
`skoda_bridge.py`:

- There is **no MQTT subscriber** anywhere in this codebase listening on
  `MQTT_DOMOTICZ_OUT_TOPIC` (it's loaded into `Config` but never read
  again after that).
- `SkodaBridge` only exposes `snapshot()` — there's no `lock()`,
  `unlock()`, `start_air_conditioning()`, `honk_flash()`, or
  `start_window_heating()` method to call even if a command did arrive.

So today, **toggling any switch in the Domoticz UI does nothing** — it's
not wired to any action, and the next poll cycle will just overwrite it
back to the polled read state anyway (or leave it alone if that field
polled `None`). This isn't a bug in the sense of crashing; it's a gap
between what's provisioned and what's implemented. Worth knowing before
you go looking for why pressing "Honk & Flash" does nothing.

`SKODA_SPIN` and `SKODA_AC_TEMPERATURE` are loaded into `Config` for the
same reason — they're clearly meant for a future control path — but
nothing in the current code reads either of them yet.

## Configuration

All required/optional environment variables, from `config.py`:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SKODA_USERNAME` | yes | — | |
| `SKODA_PASSWORD` | yes | — | |
| `SKODA_SPIN` | no | — | Loaded but currently unused (see above) |
| `DOMOTICZ_URL` | yes | — | Trailing slash stripped automatically |
| `DOMOTICZ_USER` | **yes** | — | Not optional in this codebase — Domoticz auth must be enabled |
| `DOMOTICZ_PASSWORD` | **yes** | — | |
| `MQTT_HOST` | yes | — | Your Domoticz-side MQTT broker |
| `MQTT_PORT` | no | `1883` | Note: `othervalue_as_number` — set explicitly if your broker uses a non-default port |
| `MQTT_USERNAME` | no | — | |
| `MQTT_PASSWORD` | no | — | |
| `MQTT_DOMOTICZ_OUT_TOPIC` | no | `skoda/out` | Currently unused (see limitation above) |
| `POLL_INTERVAL_SECONDS` | no | `1800` | |
| `ENABLE_GPS` | no | **`true`** | Defaults ON in this codebase — GPS position is pushed unless you explicitly set this to `false` |
| `SKODA_AC_TEMPERATURE` | no | `21.0` | Loaded but currently unused (see above) |
| `VEHICLES_CSV_PATH` | yes | — | See CSV format below |
| `DEVICES_JSON_PATH` | yes | — | Where the idx mapping is persisted |
| `LOG_LEVEL` | no | `INFO` | |
| `DOMOTICZ_PROVISION` | no | `true` | Set `false` to skip auto-provisioning entirely |
| `DOMOTICZ_HARDWARE_NAME` | no | `MySkoda` | |

### vehicles.csv format

```csv
id,name,vin
car_001,Octavia RS,TMBXXXXXXXXXXXX
car_002,SecondCar,TMBXXXXXXXXXXXX
```

`id` must be unique (enforced — a duplicate raises at startup). `name`
falls back to `id` if left blank. Both `id` and `vin` are required per
row; a row missing either raises at startup with the exact line number.

## License

MIT — see `LICENSE`.
