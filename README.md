# Docker-MQTT2Domoticz-MySkoda

**MyŠkoda API → MQTT → Domoticz bridge**

Version **0.1.0**

A lightweight Docker-based bridge that connects the unofficial Python [`myskoda`](https://github.com/skodaconnect/myskoda) library to Domoticz.

The application authenticates against MyŠkoda, retrieves vehicle information, and publishes the values to Domoticz devices. It is designed to run independently from the Domoticz installation and communicates with Domoticz through its HTTP/JSON API.

## Features

* Supports multiple Škoda vehicles.
* Uses the MyŠkoda account for authentication.
* Polls vehicle information periodically.
* Publishes vehicle status to Domoticz.
* Supports:

  * Lock status
  * Lights status
  * Doors status
  * Windows status
  * Climatisation status
  * Driving range
  * Mileage
  * Inspection due information
  * Vehicle position
* Optional vehicle controls:

  * Lock
  * Unlock
  * Wakeup
  * Honk / flash
  * Start/stop climatisation
  * Window heating
* Optional GPS position retrieval.
* Optional local MQTT output.
* Runs in Docker.
* Configuration is kept outside the container through environment variables and a vehicle CSV file.

## Architecture

```text
                  ┌─────────────────────┐
                  │      Škoda Cloud    │
                  │      MyŠkoda API    │
                  └──────────┬──────────┘
                             │
                             │ myskoda
                             ▼
                  ┌─────────────────────┐
                  │ Docker Container    │
                  │                     │
                  │ MyŠkoda → Domoticz  │
                  └──────────┬──────────┘
                             │
                   HTTP / JSON API
                             │
                             ▼
                  ┌─────────────────────┐
                  │     Domoticz        │
                  │                     │
                  │ Virtual Devices     │
                  └─────────────────────┘

                       Optional
                           │
                           ▼
                  ┌─────────────────────┐
                  │ Local MQTT Broker   │
                  │     skoda/out       │
                  └─────────────────────┘
```

## Requirements

* Docker
* Docker Compose
* A running Domoticz installation with HTTP API access
* A MyŠkoda account
* One or more Škoda vehicles associated with that account
* Network connectivity from the Docker host to:

  * Škoda services
  * Domoticz
  * MQTT broker, if MQTT output is enabled

## Installation

Clone the repository:

```bash
git clone git@github.com:janreimen/Docker-MQTT2Domoticz-MySkoda.git
cd Docker-MQTT2Domoticz-MySkoda
```

Create the environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
nano .env
```

At minimum configure:

```dotenv
SKODA_USERNAME=your-skoda-account@example.com
SKODA_PASSWORD=your-password

DOMOTICZ_URL=http://your-domoticz-url:domoticz-httpport
DOMOTICZ_USER=your-domoticz-user
DOMOTICZ_PASSWORD=your-domoticz-password
```

Do **not** commit `.env` to Git.

## Vehicle configuration

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

Do not put passwords, API credentials, or other secrets in this file.

The VIN is used to identify the vehicle in the MyŠkoda API.

## Docker Compose

The recommended deployment uses host networking:

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
```

Build and start:

```bash
docker compose build
docker compose up -d
```

Check the container:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f domoticz-myskoda
```

## Configuration

The main configuration is provided through environment variables.

### MyŠkoda

```dotenv
SKODA_USERNAME=
SKODA_PASSWORD=
SKODA_SPIN=
```

`SKODA_SPIN` is optional and is required only for operations that require the vehicle's security PIN.

### Domoticz

```dotenv
DOMOTICZ_URL=http://domoticz-url:domoticz-httpport
DOMOTICZ_USER=
DOMOTICZ_PASSWORD=
```

The bridge communicates with Domoticz through the Domoticz JSON API.

### Polling

```dotenv
POLL_INTERVAL=1800
```

The value is specified in seconds.

For example:

```text
1800 = 30 minutes
900  = 15 minutes
300  = 5 minutes
```

### GPS

```dotenv
GPS_ENABLED=true
```

Set this to `false` if vehicle position information should not be retrieved.

### Climatisation

```dotenv
AC_TARGET=21.0
```

This defines the target temperature used when starting climatisation.

### MQTT

Optional local MQTT output:

```dotenv
MQTT_HOST=ip_of_mqtt_broker
MQTT_PORT=port_of_broker
MQTT_TOPIC=skoda/out
```

## Domoticz devices

Version 0.1.0 uses predefined Domoticz IDX mappings.

The mapping is stored in:

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

### Distance values

Distance-based values such as:

* Mileage
* Driving range

are represented as **Domoticz Custom Counters** containing the current absolute value.

They are not intended to be incremented by the bridge.

For example:

```text
Mileage: 42,315 km
Range:      287 km
```

The current value is written directly to the corresponding Domoticz device.

## Vehicle controls

The bridge can expose controls for operations supported by the MyŠkoda library.

Depending on vehicle and account capabilities:

* Lock
* Unlock
* Wakeup
* Honk / flash
* Start climatisation
* Stop climatisation
* Start window heating
* Stop window heating

Vehicle commands may require the MyŠkoda security PIN.

Use these functions carefully. The bridge does not bypass Škoda's authentication or vehicle security mechanisms.

## State

Runtime device mappings are stored under:

```text
state/
```

The directory is mounted as a Docker volume so that state survives container recreation.

Do not delete the state file unless you intentionally want to recreate the device mapping.

## Logs

Follow the application logs:

```bash
docker compose logs -f
```

Or:

```bash
docker logs -f domoticz-myskoda
```

The Docker logging configuration limits log rotation to avoid uncontrolled disk usage.

## Troubleshooting

### Domoticz connection refused

Verify that Domoticz is reachable:

```bash
curl http://domoticz_ip:domoticz_port/json.htm?type=command&param=getversion
```

Check:

* Domoticz IP address
* HTTP port
* Firewall rules
* `DOMOTICZ_URL`
* Docker networking

### Domoticz returns HTTP 401

The configured Domoticz account does not have sufficient permissions for the requested API operation.

Verify:

```dotenv
DOMOTICZ_USER=
DOMOTICZ_PASSWORD=
```

and check the user's Domoticz permissions.

### MyŠkoda authentication fails

Verify:

```dotenv
SKODA_USERNAME=
SKODA_PASSWORD=
```

Also check whether the MyŠkoda account can log in normally through the official Škoda service.

### Container starts but no vehicle data appears

Check:

```bash
docker compose logs -f domoticz-myskoda
```

Then verify:

1. MyŠkoda authentication.
2. `config/vehicles.csv`.
3. VIN configuration.
4. Domoticz connectivity.
5. IDX mappings in `state/devices.json`.

## Development

The application is written in Python and packaged as a Docker image.

The main components are:

```text
app/
├── config.py
├── domoticz_client.py
├── main.py
└── ...
```

Dependencies are defined in:

```text
requirements.txt
```

Build locally:

```bash
docker compose build
```

Run:

```bash
docker compose up
```

## Version 0.1.0

Version 0.1.0 is the initial Docker release.

The device mappings are manually configured through `state/devices.json`.

Automatic Domoticz device provisioning is **not yet implemented in 0.1.0**.

## Roadmap

Planned improvements include:

* Automatic Domoticz device provisioning.
* Automatic IDX discovery and persistence.
* Easier addition of vehicles.
* Improved Domoticz device naming.
* More vehicle telemetry.
* Better error handling and retry logic.
* Improved MQTT integration.
* Additional diagnostics.
* Automated testing.

## Important notice

This project is an independent, community-developed integration.

It is not an official Škoda or Volkswagen Group product.

The MyŠkoda Python library used by this project is an unofficial interface and depends on services controlled by Škoda. API changes may therefore break functionality without notice.

## License

See [LICENSE](LICENSE).

