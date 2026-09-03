# Docker-MQTT2Domoticz-MySkoda

**MyŠkoda API → Domoticz bridge**

**Version: 0.1.1**

A lightweight Docker-based bridge that connects the MyŠkoda service to Domoticz.

The application authenticates against MyŠkoda, retrieves vehicle information, optionally executes supported vehicle commands, and publishes the resulting values to Domoticz.

Version **0.1.1** introduces **automatic Domoticz device provisioning**, eliminating the need to manually configure Domoticz IDX values.

> **Important:** This is an independent community project and is not affiliated with or endorsed by Škoda Auto or Volkswagen Group.

---

## Features

* Supports multiple Škoda vehicles.
* Uses a single authenticated MyŠkoda session for all configured vehicles.
* Periodically retrieves vehicle information.
* Automatic Domoticz hardware provisioning.
* Automatic Domoticz device provisioning.
* Automatic discovery and persistence of Domoticz IDX values.
* Automatically creates missing devices for newly configured vehicles.
* Distance values are represented as **Domoticz Custom Counters**.
* Optional GPS position retrieval.
* Optional local MQTT output.
* Optional vehicle controls:

  * Lock
  * Unlock
  * Wakeup
  * Honk / flash
  * Start/stop climatisation
  * Start/stop window heating
* Runs entirely in Docker.
* Persistent application state.

---

## Architecture

```text
                         Škoda Cloud
                             │
                             │ MyŠkoda
                             ▼
                  ┌──────────────────────┐
                  │  Docker Container    │
                  │                      │
                  │  MyŠkoda API         │
                  │        │             │
                  │        ▼             │
                  │  Domoticz Client     │
                  │        │             │
                  │        ▼             │
                  │  Provisioner         │
                  └────────┬─────────────┘
                           │
                       HTTP / JSON
                           │
                           ▼
                  ┌──────────────────────┐
                  │      Domoticz        │
                  │                      │
                  │  MySkoda Hardware    │
                  │  Vehicle Devices     │
                  └──────────────────────┘

                       Optional
                           │
                           ▼
                  ┌──────────────────────┐
                  │    Local MQTT        │
                  │    skoda/out         │
                  └──────────────────────┘
```

---

# Requirements

* Docker
* Docker Compose
* A running Domoticz installation
* Domoticz HTTP/JSON API access
* A MyŠkoda account
* One or more vehicles associated with the account
* Network connectivity to the required services

The Docker container requires network access to:

* MyŠkoda services
* Domoticz
* MQTT broker, if MQTT output is enabled

---

# Installation

Clone the repository:

```bash
git clone git@github.com:janreimen/Docker-MQTT2Domoticz-MySkoda.git
cd Docker-MQTT2Domoticz-MySkoda
```

Create the environment file:

```bash
cp .env.example .env
```

Edit the configuration:

```bash
nano .env
```

At minimum configure:

```dotenv
SKODA_USERNAME=your-skoda-account@example.com
SKODA_PASSWORD=your-password

DOMOTICZ_URL=http://domoticz-host:port
DOMOTICZ_USER=your-domoticz-user
DOMOTICZ_PASSWORD=your-domoticz-password
```

Protect the file:

```bash
chmod 600 .env
```

**Never commit `.env` to Git.**

---

# Vehicle configuration

Vehicles are configured in:

```text
config/vehicles.csv
```

Example:

```csv
vehicle_id,vin,name
car_001,YOUR_VIN_1,Octavia RS
car_002,YOUR_VIN_2,Octavia
```

The `vehicle_id` is the internal identifier used by the application.

The `vin` identifies the vehicle in MyŠkoda.

The `name` is used when creating the Domoticz devices.

Do not place passwords, tokens, PINs, or other credentials in this file.

---

# Automatic Domoticz provisioning

## Version 0.1.1

Version 0.1.1 automatically creates and configures the Domoticz hardware and devices required by the bridge.

Set:

```dotenv
DOMOTICZ_PROVISION=true
DOMOTICZ_HARDWARE_NAME=MySkoda
```

On startup the application:

1. Connects to Domoticz.
2. Finds the configured `MySkoda` hardware.
3. Creates the hardware if it does not exist.
4. Checks the configured vehicles.
5. Finds existing devices by name.
6. Creates missing devices.
7. Configures distance-based devices as Custom Counters.
8. Stores the resulting IDX mappings in `state/devices.json`.
9. Uses the stored mappings for subsequent polling.

This means that **manual IDX configuration is no longer required**.

---

# Provisioned devices

For every configured vehicle, the application provisions the following devices:

| Device         | Purpose                      |
| -------------- | ---------------------------- |
| Locked         | Vehicle lock status          |
| Lights         | Exterior lights status       |
| Doors          | Door status                  |
| Windows        | Window status                |
| Climatisation  | Climatisation status/control |
| Range          | Current driving range        |
| Mileage        | Current vehicle mileage      |
| Inspection     | Days until inspection        |
| Position       | Vehicle GPS position         |
| Honk / Flash   | Vehicle horn/lights command  |
| Window Heating | Window heating command       |
| Wakeup         | Wake-up vehicle command      |

Device names follow the pattern:

```text
<Vehicle Name> [<vehicle_id>] - <Device>
```

Example:

```text
Octavia RS [car_001] - Locked
Octavia RS [car_001] - Range
Octavia RS [car_001] - Mileage
```

---

# Distance values

Distance-based values are represented as **Custom Counters**.

This applies to:

* Mileage
* Driving range
* Other absolute distance values

The application writes the **current absolute value**.

For example:

```text
Mileage = 42,315 km
Range   = 287 km
```

The bridge does **not** increment these counters.

The Domoticz counter configuration uses:

```text
ValueQuantity = Custom
ValueUnits    = km
SwitchType    = Custom Counter
```

This is important because vehicle mileage and range represent absolute values rather than incremental consumption.

---

# Inspection

The inspection value is represented as an absolute Custom Counter.

Example:

```text
Inspection = 183 days
```

The value represents the current number of days until the next inspection.

---

# Persistent device state

Provisioned IDX values are stored in:

```text
state/devices.json
```

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

The actual IDX values are assigned by Domoticz and may differ from this example.

The state directory must therefore be persistent.

---

# Adding another vehicle

Add the vehicle to:

```text
config/vehicles.csv
```

For example:

```csv
car_003,YOUR_VIN_3,Enyaq
```

Restart the container:

```bash
docker compose restart
```

The provisioning process will detect the new vehicle and create its missing Domoticz devices.

No manual IDX configuration is required.

---

# Docker Compose

Recommended configuration:

```yaml
services:
  domoticz-myskoda:
    build: .
    container_name: domoticz-myskoda
    restart: unless-stopped
    network_mode: host
    env_file:
      - .env
    volumes:
      - ./config/vehicles.csv:/app/config/vehicles.csv:ro
      - ./state:/app/state
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    mem_limit: 128m
```

Build the container:

```bash
docker compose build
```

Start:

```bash
docker compose up -d
```

Check:

```bash
docker compose ps
```

Logs:

```bash
docker compose logs -f domoticz-myskoda
```

---

# Configuration

## MyŠkoda

```dotenv
SKODA_USERNAME=
SKODA_PASSWORD=
SKODA_SPIN=
```

`SKODA_SPIN` is optional and is only required for operations that need the vehicle security PIN.

---

## Domoticz

```dotenv
DOMOTICZ_URL=http://host_ip:port
DOMOTICZ_USER=
DOMOTICZ_PASSWORD=
```

The application communicates with Domoticz through its HTTP/JSON API.

---

## Automatic provisioning

```dotenv
DOMOTICZ_PROVISION=true
DOMOTICZ_HARDWARE_NAME=MySkoda
```

Set:

```dotenv
DOMOTICZ_PROVISION=false
```

if automatic provisioning should be disabled.

---

## Polling

```dotenv
POLL_INTERVAL=1800
```

The value is specified in seconds.

Examples:

```text
1800 = 30 minutes
900  = 15 minutes
300  = 5 minutes
```

---

## GPS

```dotenv
GPS_ENABLED=true
```

Set to:

```dotenv
GPS_ENABLED=false
```

if GPS position retrieval is not wanted.

---

## Climatisation

```dotenv
AC_TARGET=21.0
```

This is the target temperature used when starting climatisation.

---

## MQTT

Optional local MQTT output:

```dotenv
MQTT_HOST=ip_broker
MQTT_PORT=port_broker
MQTT_TOPIC=skoda/out
```

---

# Vehicle controls

Depending on vehicle and account capabilities, the bridge can expose:

* Lock
* Unlock
* Wakeup
* Honk / flash
* Start climatisation
* Stop climatisation
* Start window heating
* Stop window heating

Some commands may require `SKODA_SPIN`.

Vehicle commands should be used carefully.

The application does not bypass MyŠkoda authentication or vehicle security mechanisms.

---

# Upgrading from 0.1.0

Version 0.1.1 changes Domoticz device management from manual IDX configuration to automatic provisioning.

Before upgrading, create a backup:

```bash
cp -a state state.backup
```

Keep the existing Domoticz devices.

Do **not** delete the existing devices simply because `state/devices.json` is being regenerated.

Update the application:

```bash
git pull
```

Then rebuild:

```bash
docker compose build
```

Start:

```bash
docker compose up -d
```

Monitor provisioning:

```bash
docker compose logs -f domoticz-myskoda
```

The application will discover or create the required devices and save their IDX mappings.

---

# Troubleshooting

## Domoticz connection refused

Test Domoticz:

```bash
curl "http://domoticz:port/json.htm?type=command&param=getversion"
```

Check:

* Domoticz address
* HTTP port
* Firewall
* `DOMOTICZ_URL`
* Docker networking

---

## HTTP 401 from Domoticz

A `401 Unauthorized` response means that the configured Domoticz account does not have sufficient permissions for the requested API operation.

This is especially important for v0.1.1 because provisioning requires additional Domoticz API operations.

Check:

```dotenv
DOMOTICZ_USER=
DOMOTICZ_PASSWORD=
```

and verify the user's permissions in Domoticz.

---

## Provisioning does not create devices

Check:

```bash
docker compose logs -f domoticz-myskoda
```

Verify:

```dotenv
DOMOTICZ_PROVISION=true
DOMOTICZ_HARDWARE_NAME=MySkoda
```

Also verify that the Domoticz user is allowed to perform the required API operations.

---

## MyŠkoda authentication failure

Check:

```dotenv
SKODA_USERNAME=
SKODA_PASSWORD=
```

Verify that the account works with the normal MyŠkoda service.

---

## No vehicle data

Check:

1. MyŠkoda authentication.
2. `config/vehicles.csv`.
3. VIN.
4. Domoticz connectivity.
5. `state/devices.json`.
6. Container logs.

---

# Development

The application is written in Python and packaged as a Docker image.

Source structure:

```text
app/
├── config.py
├── domoticz_client.py
├── main.py
└── provisioner.py
```

Dependencies:

```text
requirements.txt
```

Build:

```bash
docker compose build
```

Run:

```bash
docker compose up
```

---

# Version 0.1.1

### Added

* Automatic Domoticz hardware provisioning.
* Automatic Domoticz device provisioning.
* Automatic IDX discovery.
* Persistent IDX mapping.
* Automatic provisioning for newly configured vehicles.
* Automatic Custom Counter configuration.
* Configurable provisioning settings.

### Changed

* Manual IDX configuration is no longer required.
* `state/devices.json` is generated and maintained by the application.
* Distance values are explicitly handled as absolute Custom Counters.

### Retained from 0.1.0

* MyŠkoda authentication.
* Multi-vehicle support.
* Vehicle status retrieval.
* Vehicle controls.
* Optional GPS.
* Optional MQTT.
* Docker deployment.

---

# Version 0.1.0

The initial release provided:

* Docker deployment.
* MyŠkoda integration.
* Multi-vehicle configuration.
* Domoticz integration.
* Manual IDX mapping.
* Vehicle status.
* Vehicle controls.
* Optional MQTT.
* Optional GPS.

---

# Roadmap

Potential future improvements:

* Improved provisioning compatibility across Domoticz versions.
* More vehicle telemetry.
* Improved retry and error handling.
* Automated tests.
* More MQTT functionality.
* Additional vehicle commands.
* Improved diagnostics and health monitoring.

---

# Important notice

This project is an independent community integration.

It is not an official Škoda or Volkswagen Group product.

The MyŠkoda interface depends on services controlled by Škoda. Changes to those services or APIs may therefore affect functionality without notice.

---

# License

See [LICENSE](LICENSE).


