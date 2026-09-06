# Security

This is a personal home-lab bridge, not a hardened multi-tenant service.
The notes below describe what the current code (v0.1.4) actually does
with credentials and network traffic, based on reading `config.py`,
`domoticz_client.py`, and `main.py` directly — not general best-practice
boilerplate.

## Credentials this container holds

All loaded from environment variables via `config.py`, all in plaintext
in your `.env` file:

- `SKODA_USERNAME` / `SKODA_PASSWORD` — your MySkoda account. Sent to
  Skoda's cloud auth flow by the third-party `myskoda` library; this
  project has no control over how Skoda's backend handles them beyond
  what that library does.
- `DOMOTICZ_USER` / `DOMOTICZ_PASSWORD` — **required** by this codebase's
  `config.py` (not optional), meaning your Domoticz instance's web
  authentication must be enabled for this to run at all.
- `MQTT_USERNAME` / `MQTT_PASSWORD` — optional, for your Domoticz-side
  MQTT broker. Currently unused for anything beyond being loaded (see
  README's "control devices are inert" note) — no MQTT connection is
  actually opened by this codebase yet.

**Practical steps:**
- `chmod 600 .env` and make sure it's excluded from any git history —
  don't commit it.
- Use a dedicated Domoticz user for this container if your instance
  supports per-user API restrictions, rather than an admin account,
  since `domoticz_client.py` calls `addhardware` / `createvirtualsensor`
  / `setused` (device-management endpoints), not just value updates.

## Transport

`domoticz_client.py` builds requests via `aiohttp` to whatever
`DOMOTICZ_URL` you set, with `aiohttp.BasicAuth` if a user/password is
present:

```python
auth = aiohttp.BasicAuth(self.username, self.password)
```

**Basic Auth sends credentials in a trivially reversible encoding, not
encryption.** If `DOMOTICZ_URL` is `http://` rather than `https://`,
those credentials go out in the clear on whatever network segment sits
between this container and Domoticz. If this container ends up in a DMZ
segment while Domoticz lives on an internal LAN, that credential traffic
crosses a subnet boundary — worth putting Domoticz behind TLS (even a
self-signed cert on an internal CA) before relying on this across
segments, not just within one trusted LAN.

## Data at rest

- `DEVICES_JSON_PATH` — just idx-to-device-key mappings, no credentials,
  low sensitivity.
- `VEHICLES_CSV_PATH` — contains full VINs in plaintext. VINs identify a
  specific physical vehicle; `vehicles.py` includes a `mask_vin()` helper
  used only when *logging* (`"Polling %s (%s)", vehicle.vehicle_id,
  mask_vin(vehicle.vin)`), not when the file itself is written or read —
  so the CSV on disk is unmasked. Treat it with the same file permissions
  care as `.env`.

## Known gaps (as of v0.1.4)

- No control path exists yet (see README) — so there's currently no
  attack surface via "a switch toggle triggers a vehicle action," simply
  because no switch toggle triggers anything. That changes the day
  someone wires up the `MQTT_DOMOTICZ_OUT_TOPIC` subscriber and adds
  lock/unlock methods to `SkodaBridge` — at that point, this document
  needs a real review of who can reach that MQTT topic and inject a
  lock/unlock command, especially given `SKODA_SPIN` is already being
  loaded in anticipation of exactly that.
- No rate limiting or backoff is implemented around the MySkoda poll
  loop beyond `POLL_INTERVAL_SECONDS` itself — a misconfigured short
  interval could trigger upstream rate limiting on your Skoda account
  (not modeled or protected against in this code).
- Connect to Domoticz through `HTTPS`

## Reporting a concern

This is a personal repo with a single maintainer/user — there's no
formal disclosure process. Open an issue or fix it directly.
