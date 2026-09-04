# Security Policy

## Scope

This policy covers the MySkoda → Domoticz Docker bridge, version 0.1.x.

## Reporting vulnerabilities

Please report security issues privately to the repository maintainer rather than publishing credentials, tokens, vehicle identifiers, GPS coordinates or exploit details in a public issue.

Replace this section with the maintainer's preferred private reporting address before publishing the repository.

## Secrets

Never commit:

- MySkoda username/password
- MySkoda S-PIN
- Domoticz credentials
- MQTT credentials
- vehicle VINs unless intentionally public
- GPS coordinates
- exported `.env` files

Use `.env` locally and keep it outside Git.

## Domoticz least privilege

The normal runtime account should have access only to the MySkoda devices it needs to update.

Administrative permissions are required only for provisioning operations such as creating virtual hardware and sensors.

The recommended lifecycle is:

1. Provision once with an administrative account.
2. Verify the created devices and `state/devices.json`.
3. Disable provisioning.
4. Run permanently with the restricted account.

## Vehicle controls

The underlying MySkoda API supports vehicle commands such as locking/unlocking, honking/flashing, air conditioning, window heating and wakeup. These controls can affect the physical vehicle and must be treated as privileged operations.

Do not expose the bridge's credentials or Domoticz control endpoints to untrusted networks.

## GPS

Vehicle position data is sensitive. Set:

```dotenv
ENABLE_GPS=false
```

if position data is not required.

Avoid publishing GPS coordinates to public dashboards, logs, Git repositories or public MQTT brokers.

## Logging

VINs should be masked in logs. Do not log passwords, S-PINs, session tokens or complete API responses containing sensitive information.

## MQTT

Protect the MQTT broker with authentication and network controls appropriate to the environment. Do not expose the MQTT listener directly to the Internet.

## HTTP vs HTTPS

The current configuration intentionally uses native Domoticz HTTP on the trusted LAN. HTTP should not be used across an untrusted network. If Domoticz HTTPS is deployed, use it instead and ensure certificate validation is appropriate.

## Docker

- Keep the base image and Python dependencies updated.
- Do not mount the Docker socket into this container.
- Do not run the container with unnecessary host privileges.
- Keep the state directory writable only where required.
- Review `docker-compose.yml` before deployment.

## Dependency security

The project pins `myskoda==2.17.1`. Monitor that dependency because it is an unofficial integration and depends on Škoda's changing backend services.

## Credential compromise checklist

If a credential may have leaked:

1. Change the affected password immediately.
2. Rotate any applicable S-PIN/API/MQTT credentials.
3. Replace the local `.env`.
4. Check Git history for accidental commits.
5. Review Domoticz and MQTT logs.
6. Restart the container after credentials are replaced.
