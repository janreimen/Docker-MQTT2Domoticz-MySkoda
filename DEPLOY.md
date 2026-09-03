# Deployment Guide

## Docker-MQTT2Domoticz-MySkoda

**Version 0.1.1**

This document describes deployment of the MyŠkoda → Domoticz bridge using Docker Compose.

Version 0.1.1 introduces automatic Domoticz hardware and device provisioning.

---

# 1. Prerequisites

The deployment host requires:

* Docker
* Docker Compose
* Network access to MyŠkoda
* Network access to Domoticz
* Optional access to a local MQTT broker

The Domoticz instance must have its HTTP/JSON API available.

---

# 2. Clone the repository

Using SSH:

```bash
git clone git@github.com:janreimen/Docker-MQTT2Domoticz-MySkoda.git
cd Docker-MQTT2Domoticz-MySkoda
```

Check the branch:

```bash
git branch
```

(not implemented) For the stable development/release branch:

```bash
git switch static
```

---

# 3. Configuration

Create the environment file:

```bash
cp .env.example .env
```

Edit:

```bash
nano .env
```

Example:

```dotenv
SKODA_USERNAME=your-skoda-account@example.com
SKODA_PASSWORD=your-password

DOMOTICZ_URL=http://ip_address:port
DOMOTICZ_USER=your-domoticz-user
DOMOTICZ_PASSWORD=your-domoticz-password

DOMOTICZ_PROVISION=true
DOMOTICZ_HARDWARE_NAME=MySkoda

POLL_INTERVAL=1800

GPS_ENABLED=true
AC_TARGET=21.0

MQTT_HOST=broker-ip
MQTT_PORT=broker-port
MQTT_TOPIC=skoda/out
```

Protect the file:

```bash
chmod 600 .env
```

Never commit this file.

---

# 4. Configure vehicles

Edit:

```bash
nano config/vehicles.csv
```

Example:

```csv
vehicle_id,vin,name
car_001,YOUR_VIN_1,Octavia RS
car_002,YOUR_VIN_2,Octavia
```

Each vehicle requires:

* A unique `vehicle_id`.
* The corresponding VIN.
* A readable vehicle name.

---

# 5. Persistent state

The application stores Domoticz IDX mappings in:

```text
state/devices.json
```

The Docker Compose configuration mounts:

```text
./state:/app/state
```

This is required so that device mappings survive container recreation.

Before first deployment, ensure the directory exists:

```bash
mkdir -p state
```

---

# 6. Domoticz permissions

Version 0.1.1 performs more Domoticz API operations than version 0.1.0.

The configured Domoticz account must be able to access the API operations required for:

* Reading hardware.
* Reading devices.
* Creating Dummy hardware.
* Creating virtual devices.
* Configuring devices.
* Updating device values.

If provisioning returns:

```text
HTTP 401 Unauthorized
```

the problem is normally the Domoticz account permissions rather than Docker networking.

---

# 7. Test Domoticz before starting

From the Docker host:

```bash
curl "http://ip:port/json.htm?type=command&param=getversion"
```

A successful response should contain Domoticz version information.

Test authenticated access using the configured credentials.

Do not put the password directly into shell history if this can be avoided.

---

# 8. Build

Build the image:

```bash
docker compose build
```

---

# 9. Start

Start the service:

```bash
docker compose up -d
```

Check:

```bash
docker compose ps
```

Expected:

```text
domoticz-myskoda    running
```

---

# 10. Monitor startup

Immediately check the logs:

```bash
docker compose logs -f domoticz-myskoda
```

The startup sequence should include:

1. Configuration loading.
2. MyŠkoda authentication.
3. Domoticz connection.
4. Provisioning.
5. Vehicle polling.

---

# 11. Automatic provisioning

With:

```dotenv
DOMOTICZ_PROVISION=true
```

the application automatically creates the required Domoticz structure.

The hardware name defaults to:

```text
MySkoda
```

and can be changed with:

```dotenv
DOMOTICZ_HARDWARE_NAME=MySkoda
```

The application attempts to reuse existing devices based on their configured names.

Missing devices are created automatically.

---

# 12. Verify Domoticz

After startup, open Domoticz and check the hardware list.

You should see:

```text
MySkoda
```

For each configured vehicle, devices should exist similar to:

```text
Octavia RS [car_001] - Locked
Octavia RS [car_001] - Lights
Octavia RS [car_001] - Doors
Octavia RS [car_001] - Windows
Octavia RS [car_001] - Climatisation
Octavia RS [car_001] - Range
Octavia RS [car_001] - Mileage
Octavia RS [car_001] - Inspection
Octavia RS [car_001] - Position
Octavia RS [car_001] - Honk / Flash
Octavia RS [car_001] - Window Heating
Octavia RS [car_001] - Wakeup
```

The actual IDX values are assigned by Domoticz.

---

# 13. Verify state

Check:

```bash
cat state/devices.json
```

The file should contain the assigned IDX mappings.

Example:

```json
{
  "car_001": {
    "locked": 1468,
    "lights_on": 1469,
    "doors_open": 1470,
    "windows_open": 1471,
    "climatisation": 1472,
    "range_km": 1473,
    "mileage_km": 1474,
    "inspection_due_days": 1475,
    "position": 1476,
    "honk_flash": 1477,
    "window_heating": 1478,
    "wakeup": 1479
  }
}
```

---

# 14. Add another vehicle

Edit:

```bash
nano config/vehicles.csv
```

Add:

```csv
car_003,YOUR_VIN_3,Enyaq
```

Restart:

```bash
docker compose restart
```

The application will provision the devices for the new vehicle.

No manual IDX assignment is necessary.

---

# 15. Updating the container

Pull the latest code:

```bash
git pull
```

Rebuild:

```bash
docker compose build
```

Restart:

```bash
docker compose up -d
```

Check:

```bash
docker compose logs -f domoticz-myskoda
```

---

# 16. Upgrading from version 0.1.0

Version 0.1.0 used manually configured IDX mappings.

Version 0.1.1 uses automatic provisioning and persistent IDX discovery.

Before upgrading:

```bash
cp -a state state.backup
```

If `state/devices.json` contains your old mappings, keep a backup.

Do not delete existing Domoticz devices before upgrading.

After starting 0.1.1:

```bash
docker compose logs -f domoticz-myskoda
```

Verify that the application discovers or creates the expected devices.

---

# 17. Disable provisioning

Automatic provisioning can be disabled:

```dotenv
DOMOTICZ_PROVISION=false
```

Restart:

```bash
docker compose restart
```

When disabled, the application relies on the existing device mapping in:

```text
state/devices.json
```

---

# 18. Troubleshooting

## Container is restarting

Check:

```bash
docker compose ps
docker compose logs --tail=200 domoticz-myskoda
```

---

## MyŠkoda authentication fails

Verify:

```dotenv
SKODA_USERNAME=
SKODA_PASSWORD=
```

Check that the account can authenticate normally through MyŠkoda.

---

## Domoticz connection refused

Test:

```bash
curl "http://ip:port/json.htm?type=command&param=getversion"
```

Check:

* IP address.
* Port.
* Firewall.
* Domoticz HTTP configuration.
* `DOMOTICZ_URL`.

---

## Domoticz HTTP 401

Check the Domoticz username/password and API permissions.

Provisioning requires more privileges than simply reading a few device values.

---

## Devices are not created

Check:

```bash
docker compose logs -f domoticz-myskoda
```

Verify:

```dotenv
DOMOTICZ_PROVISION=true
```

Verify that the Domoticz account has the required API permissions.

---

## Existing devices are not reused

Check:

```bash
cat state/devices.json
```

and verify that the device names in Domoticz match the configured vehicle name and `vehicle_id`.

Avoid manually renaming provisioned devices if the application is expected to identify them by name.

---

# 19. Stop

Stop the container:

```bash
docker compose down
```

The persistent state remains in:

```text
state/
```

---

# 20. Backup

At minimum back up:

```text
.env
config/vehicles.csv
state/devices.json
```

`.env` contains credentials and must be stored securely.

---

# 21. Security

See:

```text
SECURITY.md
```

Never commit:

```text
.env
```

or other credentials to Git.

Before committing changes:

```bash
git status
git diff --cached
```

